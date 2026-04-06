import whisper
import asyncio
import os
from typing import List
from ..models.schemas import SubtitleSegment

SUBTITLE_DIR = os.environ.get("SUBTITLE_DIR", "/tmp/douyin_subtitles")
os.makedirs(SUBTITLE_DIR, exist_ok=True)

_model = None


def get_model():
    global _model
    if _model is None:
        model_size = os.environ.get("WHISPER_MODEL", "medium")
        _model = whisper.load_model(model_size)
    return _model


def _format_time(seconds: float) -> str:
    """Chuyển seconds sang định dạng SRT: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _segments_to_srt(segments: list) -> str:
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _format_time(seg["start"])
        end = _format_time(seg["end"])
        text = seg["text"].strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)


async def transcribe_video(video_path: str, job_id: str) -> dict:
    """
    Dùng Whisper để trích xuất phụ đề từ video
    Trả về: { segments, srt_content, srt_path, detected_language }
    """

    def _run_whisper():
        model = get_model()
        result = model.transcribe(
            video_path,
            task="transcribe",
            verbose=False,
            fp16=False,
        )
        return result

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _run_whisper)

    segments_raw = result.get("segments", [])
    detected_lang = result.get("language", "zh")

    segments = [
        SubtitleSegment(
            index=i + 1,
            start=_format_time(seg["start"]),
            end=_format_time(seg["end"]),
            text=seg["text"].strip(),
        )
        for i, seg in enumerate(segments_raw)
    ]

    srt_content = _segments_to_srt(segments_raw)
    srt_path = os.path.join(SUBTITLE_DIR, f"{job_id}_original.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    return {
        "segments": segments,
        "srt_content": srt_content,
        "srt_path": srt_path,
        "detected_language": detected_lang,
    }
