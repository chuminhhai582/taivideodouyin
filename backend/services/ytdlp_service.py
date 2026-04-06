import yt_dlp
import asyncio
import os
import re
import requests
from typing import Optional, Callable
from ..models.schemas import VideoInfo

DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "/tmp/douyin_downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

COOKIES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cookies.txt")
BROWSERS_TO_TRY = ["chrome", "edge", "firefox"]

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.douyin.com/",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def _sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name)


def _extract_sec_user_id(url: str) -> Optional[str]:
    match = re.search(r"/user/([A-Za-z0-9_\-]+)", url)
    return match.group(1) if match else None


def _load_cookies_dict() -> dict:
    """Đọc file cookies.txt Netscape format → dict"""
    if not os.path.exists(COOKIES_FILE):
        return {}
    cookies = {}
    with open(COOKIES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) >= 7:
                cookies[parts[5]] = parts[6]
    return cookies


async def get_channel_videos(channel_url: str) -> dict:
    """Lấy danh sách video từ kênh Douyin qua Douyin Web API"""
    sec_user_id = _extract_sec_user_id(channel_url)
    if not sec_user_id:
        raise ValueError(
            "URL không hợp lệ. Dùng dạng: https://www.douyin.com/user/xxxxx"
        )

    cookies = _load_cookies_dict()
    if not cookies:
        raise ValueError(
            "Chưa có cookies. Vui lòng upload file cookies.txt trước."
        )

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch_user_videos, sec_user_id, cookies)


def _fetch_user_videos(sec_user_id: str, cookies: dict) -> dict:
    """Gọi Douyin API lấy toàn bộ video của user"""
    session = requests.Session()
    session.headers.update({
        **COMMON_HEADERS,
        "Accept": "application/json, text/plain, */*",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    })
    session.cookies.update(cookies)

    videos = []
    max_cursor = 0
    has_more = True
    channel_name = "Unknown"
    channel_id = sec_user_id

    while has_more and len(videos) < 200:
        params = {
            "sec_user_id": sec_user_id,
            "count": "20",
            "max_cursor": str(max_cursor),
            "device_platform": "webapp",
            "aid": "6383",
            "channel": "channel_pc_web",
            "update_version_code": "170400",
            "pc_client_type": "1",
            "version_code": "190500",
            "version_name": "19.5.0",
            "cookie_enabled": "true",
            "screen_width": "1920",
            "screen_height": "1080",
            "browser_language": "zh-CN",
            "browser_platform": "Win32",
            "browser_name": "Chrome",
            "browser_version": "124.0.0.0",
        }

        try:
            resp = session.get(
                "https://www.douyin.com/aweme/v1/web/aweme/post/",
                params=params,
                timeout=15,
            )
            data = resp.json()
        except Exception as e:
            raise ValueError(f"Lỗi kết nối Douyin API: {str(e)}")

        status = data.get("status_code", -1)
        if status != 0:
            msg = data.get("status_msg") or f"status_code={status}"
            raise ValueError(
                f"Douyin API lỗi: {msg}. "
                "Cookies có thể đã hết hạn, thử upload cookies mới."
            )

        aweme_list = data.get("aweme_list") or []
        has_more = bool(data.get("has_more", 0))
        max_cursor = data.get("max_cursor", 0)

        for item in aweme_list:
            vid_id = item.get("aweme_id", "")
            if not vid_id:
                continue

            author = item.get("author") or {}
            if channel_name == "Unknown":
                channel_name = author.get("nickname") or "Unknown"
            if channel_id == sec_user_id:
                channel_id = author.get("sec_uid") or sec_user_id

            cover = (item.get("video") or {}).get("cover") or {}
            thumb_urls = cover.get("url_list") or []
            thumbnail = thumb_urls[0] if thumb_urls else None

            stats = item.get("statistics") or {}
            duration_ms = (item.get("video") or {}).get("duration") or 0

            videos.append(VideoInfo(
                id=vid_id,
                title=item.get("desc") or "Untitled",
                thumbnail=thumbnail,
                duration=int(duration_ms / 1000) if duration_ms else None,
                url=f"https://www.douyin.com/video/{vid_id}",
                view_count=stats.get("play_count"),
                like_count=stats.get("digg_count"),
                upload_date=str(item.get("create_time") or ""),
            ))

        if not aweme_list:
            break

    if not videos:
        raise ValueError(
            "Không tìm thấy video. "
            "Cookies có thể hết hạn hoặc kênh không tồn tại."
        )

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
    """Tải video không watermark bằng yt-dlp"""
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

    base_opts = {
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

    def _download(opts):
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([video_url])
        for f in os.listdir(DOWNLOAD_DIR):
            if f.startswith(video_id) and f.endswith(".mp4"):
                return os.path.join(DOWNLOAD_DIR, f)
        raise FileNotFoundError(f"Không tìm thấy file sau khi tải: {video_id}")

    loop = asyncio.get_event_loop()

    # Thử cookie file trước
    if os.path.exists(COOKIES_FILE):
        try:
            return await loop.run_in_executor(
                None, _download, {**base_opts, "cookiefile": COOKIES_FILE}
            )
        except Exception:
            pass

    # Thử browser cookies
    for browser in BROWSERS_TO_TRY:
        try:
            return await loop.run_in_executor(
                None, _download, {**base_opts, "cookiesfrombrowser": (browser,)}
            )
        except Exception:
            continue

    # Không có cookies
    return await loop.run_in_executor(None, _download, base_opts)
