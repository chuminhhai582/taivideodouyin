from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from ..workers import task_worker
from ..models.schemas import JobInfo

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/", response_model=list[JobInfo])
async def list_jobs():
    """Lấy danh sách tất cả jobs"""
    return task_worker.get_all_jobs()


@router.get("/{job_id}", response_model=JobInfo)
async def get_job(job_id: str):
    """Lấy thông tin 1 job"""
    job = task_worker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy job")
    return job


@router.websocket("/ws/{job_id}")
async def job_websocket(websocket: WebSocket, job_id: str):
    """WebSocket để nhận cập nhật real-time cho 1 job"""
    await websocket.accept()
    task_worker.register_ws(job_id, websocket)

    # Gửi trạng thái hiện tại ngay khi kết nối
    job = task_worker.get_job(job_id)
    if job:
        import json
        await websocket.send_text(json.dumps({
            "job_id": job.job_id,
            "status": job.status,
            "progress": job.progress,
            "message": job.message,
            "output_path": job.output_path,
            "subtitle_vi": job.subtitle_vi,
            "error": job.error,
        }))

    try:
        while True:
            # Giữ kết nối, chờ client ping
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        task_worker.unregister_ws(job_id, websocket)


@router.websocket("/ws/all")
async def all_jobs_websocket(websocket: WebSocket):
    """WebSocket nhận cập nhật tất cả jobs"""
    await websocket.accept()
    # Đăng ký cho tất cả jobs hiện tại và mới
    task_worker.register_ws("__all__", websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        task_worker.unregister_ws("__all__", websocket)
