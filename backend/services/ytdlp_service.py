import yt_dlp
import asyncio
import os
import re
from typing import List, Optional, Callable
from ..models.schemas import VideoInfo

DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "/tmp/douyin_downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def _sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name)


async def get_channel_videos(channel_url: str) -> dict:
    """Lấy danh sách video từ kênh Douyin"""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlistend": 200,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Referer": "https://www.douyin.com/",
        },
    }

    def _extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            return info

    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, _extract)

    if not info:
        raise ValueError("Không thể lấy thông tin kênh")

    channel_name = info.get("uploader") or info.get("channel") or "Unknown"
    channel_id = info.get("uploader_id") or info.get("channel_id") or ""

    videos = []
    entries = info.get("entries", [])
    for entry in entries:
        if not entry:
            continue
        vid = VideoInfo(
            id=entry.get("id", ""),
            title=entry.get("title", "Untitled"),
            thumbnail=entry.get("thumbnail"),
            duration=entry.get("duration"),
            url=entry.get("url") or entry.get("webpage_url") or f"https://www.douyin.com/video/{entry.get('id', '')}",
            view_count=entry.get("view_count"),
            like_count=entry.get("like_count"),
            upload_date=entry.get("upload_date"),
        )
        videos.append(vid)

    return {
        "channel_name": channel_name,
        "channel_id": channel_id,
        "videos": videos,
        "total": len(videos),
    }


async def download_video(
    video_url: str,
    video_id: str,
    video_title: str,
    progress_callback: Optional[Callable] = None,
) -> str:
    """Tải video không watermark, trả về đường dẫn file"""
    safe_title = _sanitize_filename(video_title)[:50]
    output_template = os.path.join(DOWNLOAD_DIR, f"{video_id}_{safe_title}.%(ext)s")

    def _progress_hook(d):
        if d["status"] == "downloading" and progress_callback:
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            if total > 0:
                pct = int(downloaded / total * 100)
                asyncio.run_coroutine_threadsafe(
                    progress_callback(pct), asyncio.get_event_loop()
                )

    ydl_opts = {
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.douyin.com/",
        },
        "progress_hooks": [_progress_hook],
        # Douyin specific: prefer no-watermark stream
        "extractor_args": {
            "douyin": {"watermark": ["no"]}
        },
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }],
    }

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        # Tìm file vừa tải
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(video_id) and f.endswith(".mp4"):
                return os.path.join(DOWNLOAD_DIR, f)
        raise FileNotFoundError(f"Không tìm thấy file video sau khi tải: {video_id}")

    loop = asyncio.get_event_loop()
    output_path = await loop.run_in_executor(None, _download)
    return output_path
