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
    """Lấy danh sách video từ kênh Douyin"""
    sec_user_id = _extract_sec_user_id(channel_url)
    if not sec_user_id:
        raise ValueError("URL không hợp lệ. Dùng dạng: https://www.douyin.com/user/xxxxx")

    cookies = _load_cookies_dict()
    if not cookies:
        raise ValueError("Chưa có cookies. Vui lòng upload file cookies.txt trước.")

    loop = asyncio.get_event_loop()

    # Thử API trước, nếu fail thì scrape HTML
    try:
        result = await loop.run_in_executor(None, _fetch_via_api, sec_user_id, cookies)
        if result and result.get("videos"):
            return result
    except Exception:
        pass

    # Fallback: scrape từ HTML trang profile
    return await loop.run_in_executor(None, _fetch_via_html, channel_url, cookies)


def _fetch_via_html(channel_url: str, cookies: dict) -> dict:
    """Scrape danh sách video từ HTML trang profile Douyin"""
    import json as jsonlib

    session = requests.Session()
    session.headers.update({
        **COMMON_HEADERS,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Upgrade-Insecure-Requests": "1",
    })
    session.cookies.update(cookies)

    clean_url = re.sub(r'\?.*', '', channel_url.strip()).rstrip("/") + "/"
    resp = session.get(clean_url, timeout=20)
    html = resp.text

    # Tìm JSON data được nhúng trong thẻ <script id="RENDER_DATA">
    match = re.search(r'<script id="RENDER_DATA" type="application/json">(.*?)</script>', html, re.DOTALL)
    if not match:
        # Thử tìm window.__INITIAL_STATE__
        match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});\s*\(', html, re.DOTALL)

    if not match:
        raise ValueError(
            "Không thể lấy dữ liệu từ trang Douyin. "
            "Hãy export lại cookies sau khi đăng nhập và thử lại."
        )

    raw = match.group(1)
    # URL decode nếu cần
    from urllib.parse import unquote
    try:
        raw = unquote(raw)
    except Exception:
        pass

    try:
        data = jsonlib.loads(raw)
    except Exception:
        raise ValueError("Không thể parse dữ liệu từ trang Douyin.")

    # Tìm video list trong cấu trúc JSON
    videos = []
    channel_name = "Unknown"
    channel_id = ""

    def _search(obj, depth=0):
        nonlocal channel_name, channel_id
        if depth > 10 or not isinstance(obj, (dict, list)):
            return
        if isinstance(obj, list):
            for item in obj:
                _search(item, depth + 1)
            return
        # Tìm aweme_id (id video Douyin)
        if "aweme_id" in obj or ("aweme_list" in obj):
            aweme_list = obj.get("aweme_list") or ([obj] if "aweme_id" in obj else [])
            for item in aweme_list:
                if not isinstance(item, dict):
                    continue
                vid_id = item.get("aweme_id") or item.get("id")
                if not vid_id:
                    continue
                author = item.get("author") or {}
                if channel_name == "Unknown" and author.get("nickname"):
                    channel_name = author["nickname"]
                    channel_id = author.get("sec_uid") or ""
                cover = (item.get("video") or {}).get("cover") or {}
                thumb_urls = cover.get("url_list") or []
                stats = item.get("statistics") or {}
                duration_ms = (item.get("video") or {}).get("duration") or 0
                videos.append(VideoInfo(
                    id=str(vid_id),
                    title=item.get("desc") or "Untitled",
                    thumbnail=thumb_urls[0] if thumb_urls else None,
                    duration=int(duration_ms / 1000) if duration_ms else None,
                    url=f"https://www.douyin.com/video/{vid_id}",
                    view_count=(stats.get("play_count") or stats.get("view_count")),
                    like_count=stats.get("digg_count"),
                    upload_date=str(item.get("create_time") or ""),
                ))
            return
        for v in obj.values():
            _search(v, depth + 1)

    _search(data)

    if not videos:
        raise ValueError(
            "Trang tải được nhưng không tìm thấy video. "
            "Thử export cookies mới từ Chrome khi đang xem trang kênh đó."
        )

    return {
        "channel_name": channel_name,
        "channel_id": channel_id,
        "videos": videos,
        "total": len(videos),
    }


def _fetch_via_api(sec_user_id: str, cookies: dict) -> dict:
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

    # Lấy msToken từ cookies (cần thiết cho Douyin API)
    ms_token = cookies.get("msToken", "")
    ttwid = cookies.get("ttwid", "")

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
            "msToken": ms_token,
        }

        try:
            resp = session.get(
                "https://www.douyin.com/aweme/v1/web/aweme/post/",
                params=params,
                timeout=15,
            )
            raw = resp.text
            if not raw or not raw.strip():
                raise ValueError(
                    "Douyin API trả về response rỗng. "
                    "Cookies có thể hết hạn hoặc bị chặn. "
                    "Hãy đăng xuất và đăng nhập lại Douyin trên Chrome, rồi export cookies mới."
                )
            data = resp.json()
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Lỗi kết nối Douyin API: {str(e)}")

        status = data.get("status_code", -1)
        if status != 0:
            msg = data.get("status_msg") or f"status_code={status}"
            raise ValueError(
                f"Douyin API lỗi: {msg}. "
                "Thử export cookies mới từ Chrome và upload lại."
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
