from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from ..models.schemas import TikTokUploadRequest, TikTokAuthResponse
from ..services import tiktok_service
from ..workers import task_worker

router = APIRouter(prefix="/tiktok", tags=["tiktok"])


@router.get("/auth", response_model=TikTokAuthResponse)
async def get_auth_url():
    """Lấy URL để đăng nhập TikTok OAuth"""
    result = tiktok_service.get_auth_url()
    return TikTokAuthResponse(auth_url=result["auth_url"], state=result["state"])


@router.get("/callback")
async def tiktok_callback(code: str = Query(...), state: str = Query("")):
    """Callback sau khi user đăng nhập TikTok"""
    result = await tiktok_service.exchange_code_for_token(code)
    if "access_token" in result:
        # Redirect về frontend
        return RedirectResponse(url="http://localhost:3000/tiktok?status=success")
    raise HTTPException(status_code=400, detail=f"TikTok auth thất bại: {result}")


@router.get("/status")
async def auth_status():
    """Kiểm tra đã đăng nhập TikTok chưa"""
    return {"authenticated": tiktok_service.is_authenticated()}


@router.post("/upload")
async def upload_to_tiktok(req: TikTokUploadRequest):
    """Upload video đã xử lý lên TikTok"""
    job = task_worker.get_job(req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy job")
    if not job.output_path:
        raise HTTPException(status_code=400, detail="Video chưa được xử lý xong")

    import os
    if not os.path.exists(job.output_path):
        raise HTTPException(status_code=404, detail="File video không tồn tại")

    result = await tiktok_service.upload_video(
        video_path=job.output_path,
        title=req.title,
        description=req.description,
        privacy_level=req.privacy_level,
        disable_comment=req.disable_comment,
        disable_duet=req.disable_duet,
        disable_stitch=req.disable_stitch,
    )
    return result


@router.get("/upload/status/{publish_id}")
async def check_upload_status(publish_id: str):
    """Kiểm tra trạng thái upload TikTok"""
    result = await tiktok_service.check_upload_status(publish_id)
    return result
