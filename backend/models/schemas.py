from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    TRANSLATING = "translating"
    MERGING = "merging"
    UPLOADING = "uploading"
    DONE = "done"
    ERROR = "error"


class VideoInfo(BaseModel):
    id: str
    title: str
    thumbnail: Optional[str] = None
    duration: Optional[int] = None
    url: str
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    upload_date: Optional[str] = None


class ChannelVideosResponse(BaseModel):
    channel_name: str
    channel_id: str
    videos: List[VideoInfo]
    total: int


class DownloadRequest(BaseModel):
    video_ids: List[str]
    video_urls: List[str]
    auto_process: bool = True  # tự động dịch + ghép subtitle


class JobInfo(BaseModel):
    job_id: str
    video_id: str
    video_title: str
    status: JobStatus
    progress: int = 0
    message: str = ""
    output_path: Optional[str] = None
    subtitle_vi: Optional[str] = None
    error: Optional[str] = None


class SubtitleSegment(BaseModel):
    index: int
    start: str
    end: str
    text: str


class SubtitleData(BaseModel):
    job_id: str
    segments: List[SubtitleSegment]
    language: str


class TranslateRequest(BaseModel):
    job_id: str
    segments: Optional[List[SubtitleSegment]] = None  # None = dùng từ job


class MergeSubtitleRequest(BaseModel):
    job_id: str
    subtitle_content: Optional[str] = None  # None = dùng từ job
    font_size: int = 24
    font_color: str = "white"
    position: str = "bottom"  # bottom | top | center


class TikTokUploadRequest(BaseModel):
    job_id: str
    title: str
    description: str = ""
    privacy_level: str = "PUBLIC_TO_EVERYONE"
    disable_comment: bool = False
    disable_duet: bool = False
    disable_stitch: bool = False


class TikTokAuthResponse(BaseModel):
    auth_url: str
    state: str


class ProgressEvent(BaseModel):
    job_id: str
    status: JobStatus
    progress: int
    message: str
