from pydantic import BaseModel, AnyUrl, Field
from typing import List, Optional


class Segment(BaseModel):
    t_start: float = Field(..., description="Start time in seconds")
    t_end: float = Field(..., description="End time in seconds")
    title: Optional[str] = None
    snippet: str
    score: Optional[float] = None


class SearchRequest(BaseModel):
    query: str
    k: int = 3
    video_id: Optional[str] = None


class SearchResponse(BaseModel):
    results: List[Segment]
    answer: str


class IngestRequest(BaseModel):
    video_url: AnyUrl


class IngestResponse(BaseModel):
    video_id: str


class VideoInfo(BaseModel):
    video_id: str
    title: str
    url: Optional[str] = None
    created_at: Optional[str] = None
    is_local_file: bool = False


class HistoryResponse(BaseModel):
    videos: List[VideoInfo]


class UploadVideoRequest(BaseModel):
    filename: str


class UploadVideoResponse(BaseModel):
    video_id: str
    filename: str



