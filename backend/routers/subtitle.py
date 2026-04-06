from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from ..models.schemas import TranslateRequest, SubtitleData
from ..services import translate_service, whisper_service
from ..workers import task_worker
import os

router = APIRouter(prefix="/subtitle", tags=["subtitle"])


@router.get("/{job_id}/original", response_model=SubtitleData)
async def get_original_subtitle(job_id: str):
    """Lấy phụ đề gốc (tiếng Trung) của job"""
    job = task_worker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy job")

    srt_path = f"/tmp/douyin_subtitles/{job_id}_original.srt"
    if not os.path.exists(srt_path):
        raise HTTPException(status_code=404, detail="Phụ đề gốc chưa được tạo")

    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    segments = _parse_srt(content, job_id)
    return SubtitleData(job_id=job_id, segments=segments, language="zh")


@router.get("/{job_id}/vietnamese", response_model=SubtitleData)
async def get_vietnamese_subtitle(job_id: str):
    """Lấy phụ đề tiếng Việt của job"""
    job = task_worker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy job")

    srt_path = f"/tmp/douyin_subtitles/{job_id}_vi.srt"
    if not os.path.exists(srt_path):
        raise HTTPException(status_code=404, detail="Phụ đề tiếng Việt chưa được tạo")

    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    segments = _parse_srt(content, job_id)
    return SubtitleData(job_id=job_id, segments=segments, language="vi")


@router.post("/{job_id}/retranslate")
async def retranslate(job_id: str, req: TranslateRequest):
    """Dịch lại phụ đề (dùng segments tùy chỉnh hoặc từ job)"""
    job = task_worker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Không tìm thấy job")

    segments = req.segments
    if not segments:
        # Lấy từ file gốc
        srt_path = f"/tmp/douyin_subtitles/{job_id}_original.srt"
        if not os.path.exists(srt_path):
            raise HTTPException(status_code=404, detail="Không có phụ đề gốc")
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()
        segments = _parse_srt(content, job_id)

    translated = await translate_service.translate_segments(segments)
    srt_vi_path = await translate_service.save_translated_srt(translated, job_id)
    return {"status": "ok", "srt_path": srt_vi_path, "segments": translated}


@router.get("/{job_id}/download/vi")
async def download_srt(job_id: str):
    """Tải file SRT tiếng Việt"""
    srt_path = f"/tmp/douyin_subtitles/{job_id}_vi.srt"
    if not os.path.exists(srt_path):
        raise HTTPException(status_code=404, detail="File SRT chưa tồn tại")
    return FileResponse(srt_path, media_type="text/plain", filename=f"{job_id}_vi.srt")


def _parse_srt(content: str, job_id: str):
    from ..models.schemas import SubtitleSegment
    segments = []
    blocks = content.strip().split("\n\n")
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        try:
            index = int(lines[0])
            times = lines[1].split(" --> ")
            start = times[0].strip()
            end = times[1].strip()
            text = " ".join(lines[2:])
            segments.append(SubtitleSegment(index=index, start=start, end=end, text=text))
        except Exception:
            continue
    return segments
