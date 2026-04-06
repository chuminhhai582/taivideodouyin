import yt_dlp
import asyncio
import os
import re
from typing import List, Optional, Callable
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from ..models.schemas import VideoInfo

DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "/tmp/douyin_downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.douyin.com/",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def _sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name)


def _normalize_douyin_url(url: str) -> str:
    """Chuẩn hoá URL Douyin, bỏ query params thừa"""
    parsed = urlparse(url.strip())
    # Giữ lại path, bỏ query string
    clean = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    # Đảm bảo có trailing slash
    if not clean.endswith("/"):
        clean += "/"
    return clean


def _build_url_variants(url: str) -> list:
    """Tạo danh sách URL để thử lần lượt"""
    url = url.strip()
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")

    variants = [
        # Dạng chuẩn có trailing slash
        f"https://www.douyin.com{path}/",
        # Dạng không trailing slash
        f"https://www.douyin.com{path}",
        # Thử với tên miền khác
        f"https://www.iesdouyin.com{path}/",
        # URL gốc
        url,
    ]
    # Loại trùng
    seen = set()
    result = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result


async def get_channel_videos(channel_url: str) -> dict:
    """Lấy danh sách video từ kênh Douyin, thử nhiều URL variants"""

    ydl_opts = {
        "quiet": False,
        "no_warnings": False,
        "extract_flat": True,
        "playlistend": 200,
        "http_headers": COMMON_HEADERS,
        "socket_timeout": 30,
    }

    url_variants = _build_url_variants(channel_url)
    last_error = None

    def _extract(try_url: str):
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(try_url, download=False)
            return info

    loop = asyncio.get_event_loop()

    for try_url in url_variants:
        try:
            info = await loop.run_in_executor(None, _extract, try_url)
            if info:
                break
        except Exception as e:
            last_error = e
            continue
    else:
        raise ValueError(
            f"Không thể lấy thông tin kênh. "
            f"Lỗi: {str(last_error)}. "
            f"Hãy thử paste URL kênh trực tiếp từ trình duyệt."
        )

    channel_name = (
        info.get("uploader")
        or info.get("channel")
        or info.get("title")
        or "Unknown"
    )
    channel_id = info.get("uploader_id") or info.get("channel_id") or ""

    videos = []
    entries = info.get("entries") or []

    # Nếu không có entries nhưng có id thì đây là 1 video đơn lẻ
    if not entries and info.get("id"):
        entries = [info]

    for entry in entries:
        if not entry:
            continue
        vid_id = entry.get("id", "")
        vid_url = (
            entry.get("webpage_url")
            or entry.get("url")
            or (f"https://www.douyin.com/video/{vid_id}" if vid_id else "")
        )
        vid = VideoInfo(
            id=vid_id,
            title=entry.get("title") or entry.get("description") or "Untitled",
            thumbnail=entry.get("thumbnail"),
            duration=entry.get("duration"),
            url=vid_url,
            view_count=entry.get("view_count"),
            like_count=entry.get("like_count"),
            upload_date=entry.get("upload_date"),
        )
        if vid.id:
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
        "http_headers": COMMON_HEADERS,
        "progress_hooks": [_progress_hook],
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
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(video_id) and f.endswith(".mp4"):
                return os.path.join(DOWNLOAD_DIR, f)
        raise FileNotFoundError(f"Không tìm thấy file video sau khi tải: {video_id}")

    loop = asyncio.get_event_loop()
    output_path = await loop.run_in_executor(None, _download)
    return output_path
