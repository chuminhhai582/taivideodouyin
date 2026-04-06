import ffmpeg
import asyncio
import os

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/tmp/douyin_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


async def merge_subtitle(
    video_path: str,
    subtitle_path: str,
    job_id: str,
    font_size: int = 24,
    font_color: str = "white",
    position: str = "bottom",
) -> str:
    """
    Ghép phụ đề tiếng Việt vào video bằng FFmpeg (burn-in)
    Trả về đường dẫn file output
    """
    output_path = os.path.join(OUTPUT_DIR, f"{job_id}_final.mp4")

    # Map position sang alignment ASS
    alignment_map = {"bottom": 2, "top": 8, "center": 5}
    alignment = alignment_map.get(position, 2)

    # Màu chữ ASS format (AABBGGRR)
    color_map = {
        "white": "&H00FFFFFF",
        "yellow": "&H0000FFFF",
        "black": "&H00000000",
        "red": "&H000000FF",
    }
    ass_color = color_map.get(font_color, "&H00FFFFFF")

    # Build subtitle filter
    # Escape đường dẫn cho FFmpeg subtitle filter
    safe_sub_path = subtitle_path.replace("\\", "/").replace(":", "\\:")
    subtitle_filter = (
        f"subtitles='{safe_sub_path}':force_style="
        f"'FontName=Arial,FontSize={font_size},"
        f"PrimaryColour={ass_color},"
        f"Alignment={alignment},"
        f"BorderStyle=1,Outline=2,Shadow=1'"
    )

    def _run_ffmpeg():
        (
            ffmpeg
            .input(video_path)
            .output(
                output_path,
                vf=subtitle_filter,
                vcodec="libx264",
                acodec="copy",
                preset="fast",
                crf=23,
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        return output_path

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _run_ffmpeg)
    return result


async def get_video_info(video_path: str) -> dict:
    """Lấy thông tin video (duration, resolution...)"""
    def _probe():
        probe = ffmpeg.probe(video_path)
        video_stream = next(
            (s for s in probe["streams"] if s["codec_type"] == "video"), None
        )
        return {
            "duration": float(probe["format"].get("duration", 0)),
            "width": video_stream.get("width") if video_stream else 0,
            "height": video_stream.get("height") if video_stream else 0,
            "size": int(probe["format"].get("size", 0)),
        }

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _probe)
