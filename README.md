# Douyin → TikTok Việt Hóa

Ứng dụng web tải video Douyin không watermark, tự động thêm phụ đề tiếng Việt bằng AI và upload lên TikTok.

## Tính năng

- Nhập link kênh Douyin → hiển thị toàn bộ danh sách video
- Chọn 1 hoặc nhiều video để tải
- Tải video **không có watermark**
- Tự động nhận dạng giọng nói bằng **OpenAI Whisper**
- Dịch phụ đề sang **tiếng Việt** bằng **Claude AI**
- Ghép phụ đề vào video bằng **FFmpeg**
- Upload thẳng lên **TikTok** qua Content Posting API
- Theo dõi tiến trình real-time qua **WebSocket**

## Cài đặt

### Yêu cầu
- Python 3.11+
- Node.js 20+
- FFmpeg (`apt install ffmpeg` hoặc `brew install ffmpeg`)
- API Keys: Anthropic, TikTok Developer

### Cấu hình

```bash
cp .env.example .env
# Điền các API keys vào .env
```

| Biến | Mô tả |
|------|-------|
| `ANTHROPIC_API_KEY` | API key từ console.anthropic.com |
| `TIKTOK_CLIENT_KEY` | TikTok App Client Key |
| `TIKTOK_CLIENT_SECRET` | TikTok App Client Secret |
| `WHISPER_MODEL` | `tiny/base/small/medium/large-v3` (mặc định: medium) |

### Chạy development

```bash
chmod +x start.sh
./start.sh dev
```

### Chạy với Docker

```bash
./start.sh docker
```

## Truy cập

| URL | Mô tả |
|-----|-------|
| http://localhost:3000 | Giao diện web |
| http://localhost:8000/docs | Swagger API docs |

## Kiến trúc

```
Frontend (Next.js 14)     Backend (FastAPI)
─────────────────────     ─────────────────
/ (Trang chủ)        ←→  GET  /channel/videos
/jobs (Hàng đợi)     ←→  POST /download/start
/tiktok (Auth)       ←→  WS   /jobs/ws/{job_id}
                          POST /tiktok/upload
```

## Lưu ý

- TikTok API yêu cầu Business/Creator Account
- Whisper `large-v3` cho độ chính xác cao nhất nhưng cần GPU
- Video Douyin có thể bị rate-limit khi tải nhiều liên tục
