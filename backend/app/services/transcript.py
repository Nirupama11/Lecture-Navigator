from __future__ import annotations

from typing import List, Dict, Any, Tuple
from loguru import logger

from youtube_transcript_api import YouTubeTranscriptApi
import webvtt
import srt
import tempfile, os, shutil


def _clean_text(text: str) -> str:
    t = text.strip()
    # remove common filler words
    t = t.replace(" uh ", " ").replace(" um ", " ").replace(" uh.", ".").replace(" um.", ".")
    t = " ".join(t.split())
    return t


def _segment_chunks(
    sentences: List[Tuple[float, float, str]],
    window: float = 45.0,
    overlap: float = 15.0,
) -> List[Dict[str, Any]]:
    """Segment sentences into overlapping windows for retrieval."""
    segments: List[Dict[str, Any]] = []
    n = len(sentences)
    if n == 0:
        return segments

    i = 0
    while i < n:
        start = sentences[i][0]
        end = start
        texts: List[str] = []
        j = i
        while j < n and (sentences[j][1] - start) <= window:
            texts.append(sentences[j][2])
            end = sentences[j][1]
            j += 1

        snippet = _clean_text(" ".join(texts))
        if snippet:
            segments.append({
                "start_time": float(start),
                "end_time": float(end),
                "text": snippet,
                "metadata": {},
            })

        # advance index with overlap
        advance_to = start + max(window - overlap, 1.0)
        k = i
        while k < n and sentences[k][0] < advance_to:
            k += 1
        i = max(k, i + 1)

    return segments


def segment_transcript(
    sentences: List[Tuple[float, float, str]],
    window: float = 30.0,
    overlap: float = 15.0,
) -> List[Dict[str, Any]]:
    """Public wrapper to segment transcript sentences into overlapping chunks."""
    return _segment_chunks(sentences, window=window, overlap=overlap)


def load_youtube_transcript(video_url: str, window: float = 30.0, overlap: float = 15.0) -> List[Dict[str, Any]]:
    """Load YouTube transcript if available, else raise error."""
    import urllib.parse as urlparse
    parsed = urlparse.urlparse(video_url)
    qs = urlparse.parse_qs(parsed.query)
    video_id = qs.get("v", [None])[0] or parsed.path.split("/")[-1] or video_url

    if not video_id:
        raise ValueError("Invalid YouTube URL or ID")

    logger.info(f"Downloading transcript for video: {video_id}")
    
    try:
        # Try to get transcript in multiple languages
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try English first, then any available language
        try:
            transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
        except:
            # If no English, try any available transcript
            available_transcripts = list(transcript_list)
            if not available_transcripts:
                raise Exception("No transcripts available for this video")
            transcript = available_transcripts[0]
            logger.info(f"Using transcript in language: {transcript.language}")
        
        items = transcript.fetch()
        
    except Exception as e:
        logger.warning(f"Failed to get transcript for {video_id}: {e}")
        raise Exception(f"No transcript available for this video. This could be because: 1) The video has no captions/subtitles, 2) The video is private/restricted, 3) YouTube API limitations. Try using a different video or the Whisper fallback will be attempted.")
    
    sentences = [
        (float(i["start"]), float(i["start"]) + float(i["duration"]), _clean_text(i["text"]))
        for i in items
    ]
    return _segment_chunks(sentences, window=window, overlap=overlap)


def load_whisper_transcript_from_file(file_path: str, window: float = 30.0, overlap: float = 15.0) -> List[Dict[str, Any]]:
    """
    Transcribe a local video file using Whisper.
    Requires: openai-whisper, ffmpeg
    """
    import whisper
    
    if not os.path.exists(file_path):
        raise Exception(f"Video file not found: {file_path}")
    
    try:
        # Check if file exists and is not empty
        if os.path.getsize(file_path) == 0:
            raise Exception("Video file is empty")

        # Pick model based on file size
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 50:  # heuristic: use tiny for long videos
            model_name = "tiny"
        elif file_size_mb > 20:
            model_name = "base"
        else:
            model_name = "small"

        logger.info(f"Running Whisper transcription on local file with model={model_name} on {file_size_mb:.1f}MB file...")
        
        try:
            model = whisper.load_model(model_name)
            result = model.transcribe(file_path)
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise Exception(f"Audio transcription failed. This could be due to: 1) Corrupted video file, 2) Insufficient system resources, 3) Unsupported video format. Error: {str(e)}")

        # Convert to segment format
        sentences = []
        if "segments" not in result or not result["segments"]:
            raise Exception("No speech detected in the video. The video might be silent or contain only music/noise.")
            
        for seg in result["segments"]:
            start = float(seg["start"])
            end = float(seg["end"])
            text = _clean_text(seg["text"])
            if text:
                sentences.append((start, end, text))

        if not sentences:
            raise Exception("No meaningful speech content found in the video.")

        logger.info(f"Successfully transcribed {len(sentences)} segments from local file")
        return _segment_chunks(sentences, window=window, overlap=overlap)

    except Exception as e:
        if "No speech detected" in str(e) or "No meaningful speech" in str(e):
            raise e
        else:
            raise Exception(f"Failed to process local video file: {str(e)}")


def load_whisper_transcript(video_url: str, window: float = 30.0, overlap: float = 15.0) -> List[Dict[str, Any]]:
    """
    Download audio from YouTube and transcribe using Whisper (local).
    Requires: yt-dlp, openai-whisper, ffmpeg
    """
    import yt_dlp
    import whisper

    tmpdir = tempfile.mkdtemp()
    out_file = os.path.join(tmpdir, "audio")

    try:
        # Step 1: Download best audio with better error handling
        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio/best[height<=480]",
            "outtmpl": out_file + ".%(ext)s",
            "quiet": False,
            "no_warnings": False,
            "extractaudio": True,
            "audioformat": "mp3",
            "audioquality": "192K",
            "retries": 3,
            "fragment_retries": 3,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Downloading audio for Whisper: {video_url}")
            try:
                ydl.download([video_url])
            except Exception as e:
                logger.error(f"Failed to download video: {e}")
                raise Exception(f"Could not download video audio. This could be due to: 1) Video is private/restricted, 2) Geographic restrictions, 3) Video has been removed, 4) Network issues. Please try a different video.")

        # Find the downloaded file
        downloaded_files = [f for f in os.listdir(tmpdir) if f.startswith("audio")]
        if not downloaded_files:
            raise Exception("No audio file was downloaded")
        
        audio_file = os.path.join(tmpdir, downloaded_files[0])
        
        # Check if file exists and is not empty
        if not os.path.exists(audio_file) or os.path.getsize(audio_file) == 0:
            raise Exception("Downloaded audio file is empty or corrupted")

        # Step 2: Pick model based on file size
        file_size_mb = os.path.getsize(audio_file) / (1024 * 1024)
        if file_size_mb > 50:  # heuristic: use tiny for long videos
            model_name = "tiny"
        elif file_size_mb > 20:
            model_name = "base"
        else:
            model_name = "small"

        logger.info(f"Running Whisper transcription with model={model_name} on {file_size_mb:.1f}MB file...")
        
        try:
            model = whisper.load_model(model_name)
            result = model.transcribe(audio_file)
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise Exception(f"Audio transcription failed. This could be due to: 1) Corrupted audio file, 2) Insufficient system resources, 3) Audio format issues. Error: {str(e)}")

        # Step 3: Convert to segment format
        sentences = []
        if "segments" not in result or not result["segments"]:
            raise Exception("No speech detected in the audio. The video might be silent or contain only music/noise.")
            
        for seg in result["segments"]:
            start = float(seg["start"])
            end = float(seg["end"])
            text = _clean_text(seg["text"])
            if text:
                sentences.append((start, end, text))

        if not sentences:
            raise Exception("No meaningful speech content found in the video.")

        logger.info(f"Successfully transcribed {len(sentences)} segments")
        return _segment_chunks(sentences, window=window, overlap=overlap)

    finally:
        # cleanup
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass


def load_vtt(file_path: str, window: float = 30.0, overlap: float = 15.0) -> List[Dict[str, Any]]:
    sentences: List[Tuple[float, float, str]] = []
    for caption in webvtt.read(file_path):
        start = _to_seconds(caption.start)
        end = _to_seconds(caption.end)
        text = _clean_text(caption.text)
        if text:
            sentences.append((start, end, text))
    return _segment_chunks(sentences, window=window, overlap=overlap)


def load_srt(file_path: str, window: float = 30.0, overlap: float = 15.0) -> List[Dict[str, Any]]:
    sentences: List[Tuple[float, float, str]] = []
    with open(file_path, "r", encoding="utf-8") as f:
        subs = list(srt.parse(f.read()))
    for sub in subs:
        start = sub.start.total_seconds()
        end = sub.end.total_seconds()
        text = _clean_text(sub.content)
        if text:
            sentences.append((start, end, text))
    return _segment_chunks(sentences, window=window, overlap=overlap)


def _to_seconds(hhmmss: str) -> float:
    h, m, s = hhmmss.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)

