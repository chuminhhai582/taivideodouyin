#!/bin/bash
set -e

echo "=== Douyin → TikTok Việt Hóa ==="

# Kiểm tra .env
if [ ! -f ".env" ]; then
    echo "⚠️  Chưa có file .env. Tạo từ .env.example..."
    cp .env.example .env
    echo "📝 Hãy điền ANTHROPIC_API_KEY và TIKTOK credentials vào .env"
    exit 1
fi

# Tạo thư mục tạm
mkdir -p /tmp/douyin_downloads /tmp/douyin_subtitles /tmp/douyin_output

# Check xem chạy dev hay docker
if [ "$1" = "docker" ]; then
    echo "🐳 Khởi động với Docker Compose..."
    docker-compose up --build
elif [ "$1" = "dev" ]; then
    echo "🔧 Khởi động development servers..."

    # Backend
    echo "📦 Cài đặt Python dependencies..."
    cd backend
    pip install -r requirements.txt -q
    echo "🚀 Khởi động FastAPI backend (port 8000)..."
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    cd ..

    # Frontend
    echo "📦 Cài đặt Node dependencies..."
    cd frontend
    npm install -q
    echo "🌐 Khởi động Next.js frontend (port 3000)..."
    npm run dev &
    FRONTEND_PID=$!
    cd ..

    echo ""
    echo "✅ Ứng dụng đang chạy:"
    echo "   Frontend: http://localhost:3000"
    echo "   Backend:  http://localhost:8000"
    echo "   API Docs: http://localhost:8000/docs"
    echo ""
    echo "Nhấn Ctrl+C để dừng"

    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
    wait
else
    echo "Sử dụng: ./start.sh [dev|docker]"
    echo "  dev    - Chạy trực tiếp trên máy"
    echo "  docker - Chạy bằng Docker Compose"
fi
