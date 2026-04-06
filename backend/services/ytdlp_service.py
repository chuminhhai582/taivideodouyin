import yt_dlp
import asyncio
import os
import re
from typing import List, Optional, Callable
from urllib.parse import urlparse, urlunparse
from ..models.schemas import VideoInfo

DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "/tmp/douyin_downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.douyin.com/",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# Trình duyệt để thử lấy cookie (theo thứ tự ưu tiên)
BROWSERS_TO_TRY = ["chrome", "edge", "firefox", "opera", "brave", "chromium"]

# Đường dẫn file cookies.txt thủ công
COOKIES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cookies.txt")


def _sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name)


def _clean_url(url: str) -> str:
    """Bỏ query string, giữ path sạch"""
    parsed = urlparse(url.strip())
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/") + "/", "", "", ""))


def _make_ydl_opts(use_browser_cookies: Optional[str] = None, flat: bool = True) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": flat,
        "playlistend": 200,
        "http_headers": COMMON_HEADERS,
        "socket_timeout": 30,
        "ignoreerrors": True,
    }
    # Ưu tiên file cookies.txt thủ công
    if os.path.exists(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE
    elif use_browser_cookies:
        opts["cookiesfrombrowser"] = (use_browser_cookies,)
    return opts


async def get_channel_videos(channel_url: str) -> dict:
    """
    Lấy danh sách video từ kênh Douyin.
    Tự động thử lấy cookie từ Chrome/Edge nếu cần.
    """
    clean_url = _clean_url(channel_url)
    loop = asyncio.get_event_loop()

    def _extract(browser_cookie: Optional[str]) -> Optional[dict]:
        opts = _make_ydl_opts(use_browser_cookies=browser_cookie, flat=True)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(clean_url, download=False)
                return info
        except Exception:
            return None

    info = None

    # Thử 1: Không cần cookie
    info = await loop.run_in_executor(None, _extract, None)

    # Thử 2-N: Lần lượt từng trình duyệt nếu chưa lấy được video
    if not info or not _has_videos(info):
        for browser in BROWSERS_TO_TRY:
            result = await loop.run_in_executor(None, _extract, browser)
            if result and _has_videos(result):
                info = result
                break

    if not info:
        raise ValueError(
            "Không thể lấy thông tin kênh. "
            "Hãy đảm bảo bạn đang đăng nhập Douyin trên Chrome/Edge và thử lại."
        )

    channel_name = (
        info.get("uploader") or info.get("channel") or info.get("title") or "Unknown"
    )
    channel_id = info.get("uploader_id") or info.get("channel_id") or ""

    videos = []
    entries = info.get("entries") or []
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
        if not vid_id:
            continue
        videos.append(VideoInfo(
            id=vid_id,
            title=entry.get("title") or entry.get("description") or "Untitled",
            thumbnail=entry.get("thumbnail"),
            duration=entry.get("duration"),
            url=vid_url,
            view_count=entry.get("view_count"),
            like_count=entry.get("like_count"),
            upload_date=entry.get("upload_date"),
        ))

    if not videos:
        raise ValueError(
            "Kết nối được kênh nhưng không tìm thấy video. "
            "Vui lòng đăng nhập Douyin trên trình duyệt Chrome hoặc Edge rồi thử lại."
        )

    return {
        "channel_name": channel_name,
        "channel_id": channel_id,
        "videos": videos,
        "total": len(videos),
    }


def _has_videos(info: dict) -> bool:
    entries = info.get("entries") or []
    return len([e for e in entries if e and e.get("id")]) > 0


async def download_video(
    video_url: str,
    video_id: str,
    video_title: str,
    progress_callback: Optional[Callable] = None,
) -> str:
    """Tải video không watermark"""
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

    def _download(browser_cookie: Optional[str]):
        opts = {
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "merge_output_format": "mp4",
            "http_headers": COMMON_HEADERS,
            "progress_hooks": [_progress_hook],
            "extractor_args": {"douyin": {"watermark": ["no"]}},
            "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
        }
        if browser_cookie:
            opts["cookiesfrombrowser"] = (browser_cookie,)

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([video_url])

        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(video_id) and f.endswith(".mp4"):
                return os.path.join(DOWNLOAD_DIR, f)
        raise FileNotFoundError(f"Không tìm thấy file video sau khi tải: {video_id}")

    loop = asyncio.get_event_loop()

    # Thử không cookie trước, sau đó thử từng browser
    for browser in [None] + BROWSERS_TO_TRY:
        try:
            output_path = await loop.run_in_executor(None, _download, browser)
            return output_path
        except Exception as e:
            if browser == BROWSERS_TO_TRY[-1]:
                raise
            continue
