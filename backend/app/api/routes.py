from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from ..models.schemas import SearchRequest, SearchResponse, IngestRequest, IngestResponse, Segment, HistoryResponse, VideoInfo, UploadVideoResponse
from ..services import transcript as transcript_service
from ..services.search import index_segments, semantic_search, get_video_history
from ..services.agent import generate_answer
from uuid import uuid4
import urllib.parse as urlparse
import logging
import os
import tempfile
import aiofiles
import shutil

router = APIRouter()
logger = logging.getLogger(__name__)

# Create uploads directory if it doesn't exist
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

def _rid() -> str: 
    return uuid4().hex[:12]


@router.post("/search_timestamps", response_model=SearchResponse)
async def search_timestamps(payload: SearchRequest):
    if not payload.query:
        raise HTTPException(status_code=400, detail="Query is required")
    rid = _rid()
    logger.info(f"[{rid}] search: query='{payload.query}' video_id={payload.video_id}")

    try:
        docs = await semantic_search(payload.query, k=payload.k, video_id=payload.video_id)
        results = [
            Segment(
                video_id=d.get("video_id"),
                t_start=float(d.get("start_time", 0.0)),
                t_end=float(d.get("end_time", 0.0)),
                title=d.get("title"),
                snippet=d.get("snippet") or d.get("text", ""),
                score=float(d.get("score", 0.0)),
            )
            for d in docs
        ]

        answer = await generate_answer(payload.query, docs)
        resp = SearchResponse(results=results, answer=answer)
        logger.info(f"[{rid}] search returned {len(results)} results")
        return resp

    except Exception as e:
        logger.exception(f"[{rid}] search_timestamps failed")
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")


@router.post("/ingest_video", response_model=IngestResponse)
async def ingest_video(payload: IngestRequest):
    if not payload.video_url:
        raise HTTPException(status_code=400, detail="video_url is required")
    rid = _rid()
    logger.info(f"[{rid}] ingest_video url={payload.video_url}")

    transcript_method = "unknown"
    try:
        # Always use Whisper transcription for public YouTube videos
        import yt_dlp
        import tempfile, os, subprocess
        with tempfile.TemporaryDirectory() as tmpdir:
            # Try bestaudio+bestvideo, fallback to bestaudio if video fails
            video_path = None
            yt_dlp_errors = []
            for ydl_format in [
                'bestaudio+bestvideo/best',
                'bestaudio/best',
                'best'
            ]:
                ydl_opts = {
                    'format': ydl_format,
                    'outtmpl': os.path.join(tmpdir, '%(id)s.%(ext)s'),
                    'quiet': True,
                    'merge_output_format': 'mp4',
                }
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(str(payload.video_url), download=True)
                        video_path = ydl.prepare_filename(info)
                    logger.info(f"[{rid}] Downloaded YouTube video to {video_path} with format {ydl_format}")
                    break
                except Exception as e:
                    yt_dlp_errors.append(f"Format {ydl_format}: {e}")
                    video_path = None
            if not video_path or not os.path.exists(video_path):
                logger.error(f"[{rid}] yt-dlp failed for all formats: {yt_dlp_errors}")
                raise Exception(f"Failed to download video. yt-dlp errors: {yt_dlp_errors}")

            # Check for audio stream using ffprobe before Whisper
            ffprobe_cmd = [
                'ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index',
                '-of', 'csv=p=0', video_path
            ]
            try:
                result = subprocess.run(ffprobe_cmd, capture_output=True, text=True, check=True)
                logger.info(f"[{rid}] ffprobe output: {result.stdout.strip()}")
                if not result.stdout.strip():
                    raise Exception("Downloaded video file does not contain an audio stream. Try a different video or check yt-dlp options.")
            except Exception as ffprobe_error:
                logger.error(f"[{rid}] ffprobe audio check failed: {ffprobe_error}")
                raise Exception(f"Audio stream check failed: {ffprobe_error}")

            raw_segments = transcript_service.load_whisper_transcript_from_file(video_path)
            logger.info(f"[{rid}] Successfully loaded Whisper transcript from downloaded video")
            transcript_method = "whisper_downloaded"

        # Validate segments
        if not raw_segments:
            raise Exception("No transcript content was extracted from the video. The video might be silent, contain only music, or have processing restrictions.")

        # Normalize format
        if raw_segments and isinstance(raw_segments[0], dict) and "text" in raw_segments[0]:
            segments = raw_segments
        else:
            segments = transcript_service.segment_transcript(raw_segments)

        if not segments:
            raise Exception("No meaningful content segments were created from the transcript. The video might not contain speech or the content might be too short.")

        # Parse video ID
        parsed = urlparse.urlparse(str(payload.video_url))
        qs = urlparse.parse_qs(parsed.query)
        video_id = qs.get("v", [None])[0] or parsed.path.split("/")[-1] or str(payload.video_url)
        title = f"YouTube {video_id} ({transcript_method})"

        # Index in vector store
        await index_segments(video_id, title, segments, str(payload.video_url), False)
        logger.info(f"[{rid}] Successfully indexed {len(segments)} segments for {video_id} using {transcript_method}")
        return IngestResponse(video_id=video_id)

    except Exception as e:
        error_msg = str(e)
        logger.exception(f"[{rid}] ingest_video failed with method {transcript_method}")
        
        # Provide helpful error messages based on common issues
        if "private" in error_msg.lower() or "restricted" in error_msg.lower():
            user_msg = "This video appears to be private or restricted. Please try a public video."
        elif "not available" in error_msg.lower() or "removed" in error_msg.lower():
            user_msg = "This video is not available or may have been removed. Please try a different video."
        elif "geographic" in error_msg.lower():
            user_msg = "This video is not available in your region due to geographic restrictions."
        elif "empty" in error_msg.lower() or "silent" in error_msg.lower():
            user_msg = "This video appears to be silent or contains no speech content that can be processed."
        elif "transcript" in error_msg.lower() and "captions" in error_msg.lower():
            user_msg = "This video has no available captions or transcripts. Please try a video with subtitles or captions enabled."
        else:
            user_msg = f"Failed to process video: {error_msg}"
            
        raise HTTPException(status_code=400, detail=user_msg)


@router.get("/history", response_model=HistoryResponse)
async def get_history():
    """Get list of all processed videos"""
    try:
        videos_data = await get_video_history()
        videos = [
            VideoInfo(
                video_id=v["video_id"],
                title=v["title"],
                url=v.get("url"),
                created_at=v.get("created_at"),
                is_local_file=v.get("is_local_file", False)
            )
            for v in videos_data
        ]
        return HistoryResponse(videos=videos)
    except Exception as e:
        logger.exception("get_history failed")
        raise HTTPException(status_code=500, detail=f"Failed to get history: {e}")


@router.post("/upload_video", response_model=UploadVideoResponse)
async def upload_video(file: UploadFile = File(...)):
    """Upload and process a local video file"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    rid = _rid()
    logger.info(f"[{rid}] upload_video filename={file.filename}")
    
    # Check file extension
    allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v', '.flv', '.wmv'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}")
    
    try:
        # Generate video ID and permanent file path
        video_id = f"local_{uuid4().hex[:8]}_{os.path.splitext(file.filename)[0]}"
        safe_filename = f"{video_id}{file_ext}"
        permanent_path = os.path.join(UPLOADS_DIR, safe_filename)
        
        # Save uploaded file permanently
        async with aiofiles.open(permanent_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        try:
            # Process with Whisper (since it's a local file)
            raw_segments = transcript_service.load_whisper_transcript_from_file(permanent_path)
            
            # Normalize format
            if raw_segments and isinstance(raw_segments[0], dict) and "text" in raw_segments[0]:
                segments = raw_segments
            else:
                segments = transcript_service.segment_transcript(raw_segments)
            
            title = f"Local: {file.filename}"
            
            # Index in vector store with file path for later retrieval
            await index_segments(video_id, title, segments, safe_filename, True)
            logger.info(f"[{rid}] indexed {len(segments)} segments for local file {file.filename}")
            
            return UploadVideoResponse(video_id=video_id, filename=file.filename)
            
        except Exception as e:
            # If processing fails, clean up the saved file
            try:
                os.unlink(permanent_path)
            except:
                pass
            raise e
                
    except Exception as e:
        logger.exception(f"[{rid}] upload_video failed")
        raise HTTPException(status_code=400, detail=f"Failed to process video: {e}")


@router.get("/video/{filename}")
async def serve_video(filename: str):
    """Serve uploaded video files"""
    # Security: only allow files that exist and have safe names
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    file_path = os.path.join(UPLOADS_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    # Get file extension to set proper content type
    ext = os.path.splitext(filename)[1].lower()
    media_type_map = {
        '.mp4': 'video/mp4',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime',
        '.mkv': 'video/x-matroska',
        '.webm': 'video/webm',
        '.m4v': 'video/mp4',
        '.flv': 'video/x-flv',
        '.wmv': 'video/x-ms-wmv'
    }
    
    media_type = media_type_map.get(ext, 'video/mp4')
    
    return FileResponse(
        file_path,
        media_type=media_type,
        headers={"Accept-Ranges": "bytes"}
    )
