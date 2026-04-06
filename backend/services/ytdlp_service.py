import yt_dlp
import asyncio
import os
import re
import json as jsonlib
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


def _load_cookies_for_playwright() -> list:
    """Đọc cookies.txt Netscape format → list dicts cho Playwright"""
    if not os.path.exists(COOKIES_FILE):
        return []
    cookies = []
    with open(COOKIES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            domain = parts[0]
            http_only = parts[1].upper() == "TRUE"
            path = parts[2]
            secure = parts[3].upper() == "TRUE"
            expires = int(parts[4]) if parts[4].isdigit() else -1
            name = parts[5]
            value = parts[6]
            if not name:
                continue
            cookie = {
                "name": name,
                "value": value,
                "domain": domain.lstrip("."),
                "path": path,
                "secure": secure,
                "httpOnly": http_only,
            }
            if expires > 0:
                cookie["expires"] = expires
            cookies.append(cookie)
    return cookies


async def get_channel_videos(channel_url: str) -> dict:
    """Lấy danh sách video từ kênh Douyin bằng Playwright"""
    sec_user_id = _extract_sec_user_id(channel_url)
    if not sec_user_id:
        raise ValueError("URL không hợp lệ. Dùng dạng: https://www.douyin.com/user/xxxxx")

    if not os.path.exists(COOKIES_FILE):
        raise ValueError("Chưa có cookies. Vui lòng upload file cookies.txt trước.")

    try:
        import playwright
    except ImportError:
        raise ValueError(
            "Chưa cài Playwright. Chạy: py -m pip install playwright && py -m playwright install chromium"
        )

    clean_url = re.sub(r'\?.*', '', channel_url.strip()).rstrip("/") + "/"
    cookies = _load_cookies_for_playwright()

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _scrape_with_playwright_sync, clean_url, cookies, sec_user_id)


def _scrape_with_playwright_sync(clean_url: str, cookies: list, sec_user_id: str) -> dict:
    """Dùng Playwright sync API trong thread riêng (tương thích Windows)"""
    from playwright.sync_api import sync_playwright

    videos = []
    channel_name = "Unknown"
    channel_id = sec_user_id
    captured = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=COMMON_HEADERS["User-Agent"],
            locale="zh-CN",
            viewport={"width": 1920, "height": 1080},
        )

        if cookies:
            context.add_cookies(cookies)

        page = context.new_page()

        def handle_response(response):
            if "aweme/v1/web/aweme/post" in response.url:
                try:
                    body = response.json()
                    if body.get("status_code") == 0:
                        captured.append(body)
                except Exception:
                    pass

        page.on("response", handle_response)

        page.goto(clean_url, wait_until="networkidle", timeout=30000)

        # Scroll xuống để load thêm video
        for _ in range(6):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1500)

        browser.close()

    for resp_data in captured:
        for item in (resp_data.get("aweme_list") or []):
            vid_id = item.get("aweme_id", "")
            if not vid_id:
                continue
            author = item.get("author") or {}
            if channel_name == "Unknown":
                channel_name = author.get("nickname") or "Unknown"
                channel_id = author.get("sec_uid") or sec_user_id
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
                view_count=stats.get("play_count"),
                like_count=stats.get("digg_count"),
                upload_date=str(item.get("create_time") or ""),
            ))

    if not videos:
        raise ValueError(
            "Không tìm thấy video. Cookies có thể hết hạn. "
            "Hãy đăng xuất, đăng nhập lại Douyin rồi export cookies mới."
        )

    seen = set()
    unique = []
    for v in videos:
        if v.id not in seen:
            seen.add(v.id)
            unique.append(v)

    return {
        "channel_name": channel_name,
        "channel_id": channel_id,
        "videos": unique,
        "total": len(unique),
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

    if os.path.exists(COOKIES_FILE):
        try:
            return await loop.run_in_executor(
                None, _download, {**base_opts, "cookiefile": COOKIES_FILE}
            )
        except Exception:
            pass

    for browser in BROWSERS_TO_TRY:
        try:
            return await loop.run_in_executor(
                None, _download, {**base_opts, "cookiesfrombrowser": (browser,)}
            )
        except Exception:
            continue

    return await loop.run_in_executor(None, _download, base_opts)
