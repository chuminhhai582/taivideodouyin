from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import shutil

router = APIRouter(prefix="/settings", tags=["settings"])

COOKIES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cookies.txt")


@router.post("/cookies/upload")
async def upload_cookies(file: UploadFile = File(...)):
    """Upload file cookies.txt từ trình duyệt"""
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .txt")

    with open(COOKIES_FILE, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"status": "ok", "message": "Đã lưu cookies thành công!"}


@router.get("/cookies/status")
async def cookies_status():
    """Kiểm tra có file cookies chưa"""
    exists = os.path.exists(COOKIES_FILE)
    size = os.path.getsize(COOKIES_FILE) if exists else 0
    return {"has_cookies": exists, "size_bytes": size}


@router.delete("/cookies")
async def delete_cookies():
    """Xóa file cookies"""
    if os.path.exists(COOKIES_FILE):
        os.remove(COOKIES_FILE)
    return {"status": "ok", "message": "Đã xóa cookies"}
