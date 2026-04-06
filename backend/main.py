from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os

load_dotenv()

from .routers import channel, download, jobs, subtitle, tiktok, settings

app = FastAPI(
    title="Douyin → TikTok Việt Hóa",
    description="Tải video Douyin, thêm phụ đề tiếng Việt và đăng lên TikTok",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(channel.router)
app.include_router(download.router)
app.include_router(jobs.router)
app.include_router(subtitle.router)
app.include_router(tiktok.router)
app.include_router(settings.router)

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/tmp/douyin_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
app.mount("/files", StaticFiles(directory=OUTPUT_DIR), name="files")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "douyin-tiktok-api"}
