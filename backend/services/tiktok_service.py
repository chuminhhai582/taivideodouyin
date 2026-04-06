import httpx
import os
import asyncio
import secrets
from urllib.parse import urlencode

TIKTOK_CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET", "")
TIKTOK_REDIRECT_URI = os.environ.get("TIKTOK_REDIRECT_URI", "http://localhost:3000/tiktok/callback")

TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_UPLOAD_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
TIKTOK_UPLOAD_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

# In-memory token store (production: dùng Redis/DB)
_token_store: dict = {}


def get_auth_url() -> dict:
    """Tạo URL OAuth TikTok"""
    state = secrets.token_urlsafe(16)
    params = {
        "client_key": TIKTOK_CLIENT_KEY,
        "response_type": "code",
        "scope": "user.info.basic,video.publish",
        "redirect_uri": TIKTOK_REDIRECT_URI,
        "state": state,
    }
    auth_url = f"{TIKTOK_AUTH_URL}?{urlencode(params)}"
    return {"auth_url": auth_url, "state": state}


async def exchange_code_for_token(code: str) -> dict:
    """Đổi authorization code lấy access token"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TIKTOK_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "client_key": TIKTOK_CLIENT_KEY,
                "client_secret": TIKTOK_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": TIKTOK_REDIRECT_URI,
            },
        )
        data = resp.json()
        if "access_token" in data:
            _token_store["access_token"] = data["access_token"]
            _token_store["refresh_token"] = data.get("refresh_token", "")
            _token_store["open_id"] = data.get("open_id", "")
        return data


async def upload_video(
    video_path: str,
    title: str,
    description: str = "",
    privacy_level: str = "PUBLIC_TO_EVERYONE",
    disable_comment: bool = False,
    disable_duet: bool = False,
    disable_stitch: bool = False,
) -> dict:
    """Upload video lên TikTok qua Direct Post API"""
    access_token = _token_store.get("access_token")
    if not access_token:
        raise ValueError("Chưa đăng nhập TikTok. Vui lòng authorize trước.")

    file_size = os.path.getsize(video_path)
    chunk_size = 10 * 1024 * 1024  # 10MB chunks

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }

    # Bước 1: Init upload
    async with httpx.AsyncClient() as client:
        init_payload = {
            "post_info": {
                "title": title[:150],
                "description": description[:2200],
                "privacy_level": privacy_level,
                "disable_comment": disable_comment,
                "disable_duet": disable_duet,
                "disable_stitch": disable_stitch,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": file_size,
                "chunk_size": chunk_size,
                "total_chunk_count": (file_size + chunk_size - 1) // chunk_size,
            },
        }

        init_resp = await client.post(
            TIKTOK_UPLOAD_INIT_URL,
            headers=headers,
            json=init_payload,
        )
        init_data = init_resp.json()

        if init_data.get("error", {}).get("code") != "ok":
            raise ValueError(f"TikTok init upload lỗi: {init_data}")

        upload_url = init_data["data"]["upload_url"]
        publish_id = init_data["data"]["publish_id"]

    # Bước 2: Upload chunks
    async with httpx.AsyncClient(timeout=300) as client:
        with open(video_path, "rb") as f:
            chunk_index = 0
            offset = 0
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                end_offset = min(offset + len(chunk) - 1, file_size - 1)
                upload_headers = {
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {offset}-{end_offset}/{file_size}",
                }
                await client.put(upload_url, headers=upload_headers, content=chunk)
                offset += len(chunk)
                chunk_index += 1

    return {"publish_id": publish_id, "status": "uploading"}


async def check_upload_status(publish_id: str) -> dict:
    """Kiểm tra trạng thái upload TikTok"""
    access_token = _token_store.get("access_token")
    if not access_token:
        raise ValueError("Chưa đăng nhập TikTok")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TIKTOK_UPLOAD_STATUS_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={"publish_id": publish_id},
        )
        return resp.json()


def is_authenticated() -> bool:
    return bool(_token_store.get("access_token"))
