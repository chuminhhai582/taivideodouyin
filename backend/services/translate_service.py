import asyncio
import os
from typing import List
from deep_translator import GoogleTranslator
from ..models.schemas import SubtitleSegment

SUBTITLE_DIR = os.environ.get("SUBTITLE_DIR", "/tmp/douyin_subtitles")
os.makedirs(SUBTITLE_DIR, exist_ok=True)

BATCH_SIZE = 50  # Google Translate xử lý được nhiều hơn mỗi lần


def _segments_to_srt(segments: List[SubtitleSegment]) -> str:
    lines = []
    for seg in segments:
        lines.append(f"{seg.index}\n{seg.start} --> {seg.end}\n{seg.text}\n")
    return "\n".join(lines)


async def translate_segments(
    segments: List[SubtitleSegment],
    source_lang: str = "zh-CN",
    target_lang: str = "vi",
) -> List[SubtitleSegment]:
    """Dịch phụ đề sang tiếng Việt bằng Google Translate (miễn phí, không cần API key)"""

    # Map mã ngôn ngữ Whisper → Google Translate
    lang_map = {
        "zh": "zh-CN",
        "chinese": "zh-CN",
        "en": "en",
        "ja": "ja",
        "ko": "ko",
    }
    src = lang_map.get(source_lang, "zh-CN")

    def _translate_batch(texts: List[str]) -> List[str]:
        # Ghép các dòng bằng ký tự phân cách đặc biệt để dịch 1 lần
        SEPARATOR = " ||| "
        combined = SEPARATOR.join(texts)
        translator = GoogleTranslator(source=src, target=target_lang)
        translated = translator.translate(combined)
        if not translated:
            return texts
        parts = translated.split("|||")
        # Đảm bảo đủ số dòng
        result = [p.strip() for p in parts]
        while len(result) < len(texts):
            result.append(texts[len(result)])
        return result[:len(texts)]

    translated_all = []
    loop = asyncio.get_event_loop()

    for i in range(0, len(segments), BATCH_SIZE):
        batch = segments[i:i + BATCH_SIZE]
        texts = [seg.text for seg in batch]

        translated_texts = await loop.run_in_executor(None, _translate_batch, texts)

        for seg, translated_text in zip(batch, translated_texts):
            translated_all.append(SubtitleSegment(
                index=seg.index,
                start=seg.start,
                end=seg.end,
                text=translated_text,
            ))

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
