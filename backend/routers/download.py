from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from ..models.schemas import DownloadRequest
from ..workers import task_worker
import os

router = APIRouter(prefix="/download", tags=["download"])


@router.post("/start")
async def start_download(req: DownloadRequest):
    """Bắt đầu tải và xử lý các video đã chọn"""
    if not req.video_ids or len(req.video_ids) != len(req.video_urls):
        raise HTTPException(status_code=400, detail="video_ids và video_urls phải có cùng số lượng")

    job_ids = []
    for vid_id, vid_url in zip(req.video_ids, req.video_urls):
        job_id = await task_worker.create_and_run_job(
            video_id=vid_id,
            video_url=vid_url,
            video_title=f"Video_{vid_id}",
            auto_process=req.auto_process,
        )
        job_ids.append(job_id)

    return {"job_ids": job_ids, "total": len(job_ids)}


@router.get("/file/{job_id}")
async def download_file(job_id: str):
    """Tải file video đã xử lý về máy"""
    job = task_worker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy job")
    if not job.output_path or not os.path.exists(job.output_path):
        raise HTTPException(status_code=404, detail="File chưa sẵn sàng")

    return FileResponse(
        path=job.output_path,
        media_type="video/mp4",
        filename=os.path.basename(job.output_path),
    )
