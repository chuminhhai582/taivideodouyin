import anthropic
import asyncio
import os
import re
from typing import List
from ..models.schemas import SubtitleSegment

SUBTITLE_DIR = os.environ.get("SUBTITLE_DIR", "/tmp/douyin_subtitles")
os.makedirs(SUBTITLE_DIR, exist_ok=True)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
BATCH_SIZE = 30  # Số segment dịch mỗi lần gọi API


def _segments_to_srt(segments: List[SubtitleSegment]) -> str:
    lines = []
    for seg in segments:
        lines.append(f"{seg.index}\n{seg.start} --> {seg.end}\n{seg.text}\n")
    return "\n".join(lines)


def _parse_translated_batch(raw: str, original_segments: List[SubtitleSegment]) -> List[SubtitleSegment]:
    """Parse kết quả dịch từ Claude, ghép lại với timestamp gốc"""
    lines = [l.strip() for l in raw.strip().split("\n") if l.strip()]
    translated = []
    for i, seg in enumerate(original_segments):
        text = lines[i] if i < len(lines) else seg.text
        translated.append(SubtitleSegment(
            index=seg.index,
            start=seg.start,
            end=seg.end,
            text=text,
        ))
    return translated


async def translate_segments(
    segments: List[SubtitleSegment],
    source_lang: str = "zh",
    target_lang: str = "vi",
) -> List[SubtitleSegment]:
    """Dịch các segment phụ đề sang tiếng Việt bằng Claude API"""
    if not ANTHROPIC_API_KEY:
        raise ValueError("Chưa cấu hình ANTHROPIC_API_KEY")

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    translated_all = []

    # Chia batch để tránh vượt token limit
    for i in range(0, len(segments), BATCH_SIZE):
        batch = segments[i:i + BATCH_SIZE]
        texts = "\n".join(seg.text for seg in batch)

        prompt = f"""Dịch các dòng phụ đề sau từ tiếng Trung sang tiếng Việt.
Yêu cầu quan trọng:
- Mỗi dòng đầu vào tương ứng đúng 1 dòng đầu ra
- Giữ nguyên số lượng dòng, KHÔNG thêm hoặc bỏ dòng nào
- Dịch tự nhiên, phù hợp với ngữ cảnh video
- Không thêm giải thích, chỉ trả về bản dịch

Phụ đề cần dịch:
{texts}"""

        message = await client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        translated_text = message.content[0].text
        translated_batch = _parse_translated_batch(translated_text, batch)
        translated_all.extend(translated_batch)

    return translated_all


async def save_translated_srt(
    segments: List[SubtitleSegment],
    job_id: str,
) -> str:
    """Lưu SRT tiếng Việt và trả về đường dẫn"""
    srt_content = _segments_to_srt(segments)
    srt_path = os.path.join(SUBTITLE_DIR, f"{job_id}_vi.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)
    return srt_path
