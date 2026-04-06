"""
Worker xử lý các tác vụ bất đồng bộ: download, transcribe, translate, merge
Dùng asyncio + in-memory job store (production: dùng Celery + Redis)
"""
import asyncio
import uuid
import os
from typing import Dict, Optional
from ..models.schemas import JobInfo, JobStatus
from ..services import ytdlp_service, whisper_service, translate_service, ffmpeg_service

# In-memory job store
_jobs: Dict[str, JobInfo] = {}
# WebSocket connections {job_id: set of websocket}
_ws_connections: Dict[str, set] = {}


def get_job(job_id: str) -> Optional[JobInfo]:
    return _jobs.get(job_id)


def get_all_jobs() -> list:
    return list(_jobs.values())


def register_ws(job_id: str, ws):
    if job_id not in _ws_connections:
        _ws_connections[job_id] = set()
    _ws_connections[job_id].add(ws)


def unregister_ws(job_id: str, ws):
    if job_id in _ws_connections:
        _ws_connections[job_id].discard(ws)


async def _broadcast(job: JobInfo):
    """Push cập nhật tới tất cả WebSocket client đang theo dõi job này"""
    if job.job_id not in _ws_connections:
        return
    import json
    msg = json.dumps({
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "output_path": job.output_path,
        "subtitle_vi": job.subtitle_vi,
        "error": job.error,
    })
    dead = set()
    for ws in _ws_connections[job.job_id]:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.add(ws)
    _ws_connections[job.job_id] -= dead


async def _update_job(job: JobInfo, status: JobStatus, progress: int, message: str, **kwargs):
    job.status = status
    job.progress = progress
    job.message = message
    for k, v in kwargs.items():
        setattr(job, k, v)
    await _broadcast(job)


async def create_and_run_job(
    video_id: str,
    video_url: str,
    video_title: str,
    auto_process: bool = True,
) -> str:
    """Tạo job mới và chạy pipeline async"""
    job_id = f"{video_id}_{uuid.uuid4().hex[:8]}"
    job = JobInfo(
        job_id=job_id,
        video_id=video_id,
        video_title=video_title,
        status=JobStatus.PENDING,
        progress=0,
        message="Đang chờ xử lý...",
    )
    _jobs[job_id] = job

    # Chạy pipeline bất đồng bộ
    asyncio.create_task(_run_pipeline(job, video_url, auto_process))
    return job_id


async def _run_pipeline(job: JobInfo, video_url: str, auto_process: bool):
    try:
        # ── Bước 1: Download ──────────────────────────────────────────
        await _update_job(job, JobStatus.DOWNLOADING, 5, "Đang tải video...")

        async def on_download_progress(pct: int):
            await _update_job(job, JobStatus.DOWNLOADING, int(pct * 0.4), f"Đang tải... {pct}%")

        video_path = await ytdlp_service.download_video(
            video_url, job.video_id, job.video_title, on_download_progress
        )
        await _update_job(job, JobStatus.DOWNLOADING, 40, f"Tải xong: {os.path.basename(video_path)}", output_path=video_path)

        if not auto_process:
            await _update_job(job, JobStatus.DONE, 100, "Tải video hoàn tất!", output_path=video_path)
            return

        # ── Bước 2: Transcribe ────────────────────────────────────────
        await _update_job(job, JobStatus.TRANSCRIBING, 45, "Đang nhận dạng giọng nói (Whisper)...")
        transcribe_result = await whisper_service.transcribe_video(video_path, job.job_id)
        segments = transcribe_result["segments"]
        srt_original_path = transcribe_result["srt_path"]
        await _update_job(job, JobStatus.TRANSCRIBING, 60, f"Nhận dạng xong ({len(segments)} đoạn)")

        # ── Bước 3: Translate ─────────────────────────────────────────
        await _update_job(job, JobStatus.TRANSLATING, 62, "Đang dịch sang tiếng Việt...")
        translated_segments = await translate_service.translate_segments(
            segments,
            source_lang=transcribe_result.get("detected_language", "zh"),
        )
        srt_vi_path = await translate_service.save_translated_srt(translated_segments, job.job_id)
        await _update_job(job, JobStatus.TRANSLATING, 75, "Dịch xong!", subtitle_vi=srt_vi_path)

        # ── Bước 4: Merge subtitle ────────────────────────────────────
        await _update_job(job, JobStatus.MERGING, 78, "Đang ghép phụ đề vào video...")
        final_path = await ffmpeg_service.merge_subtitle(video_path, srt_vi_path, job.job_id)
        await _update_job(
            job, JobStatus.DONE, 100,
            "Hoàn tất! Video đã sẵn sàng.",
            output_path=final_path,
        )

    except Exception as e:
        await _update_job(job, JobStatus.ERROR, 0, f"Lỗi: {str(e)}", error=str(e))
