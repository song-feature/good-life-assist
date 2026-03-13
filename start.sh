#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Check .env
if [ ! -f .env ]; then
    cp .env.example .env
    echo "[INFO] .env 已从 .env.example 创建，请编辑填入 LLM_API_KEY"
fi

# Ensure data dir
mkdir -p data

# Install backend deps
echo "[INFO] 安装后端依赖..."
uv sync --quiet

# Install frontend deps
echo "[INFO] 安装前端依赖..."
cd web && npm install --silent 2>/dev/null && cd ..

# Start backend
echo "[INFO] 启动后端服务 :8000 ..."
uv run python -m server.main &
BACKEND_PID=$!

# Start frontend
echo "[INFO] 启动前端服务 :5173 ..."
cd web && npm run dev &
FRONTEND_PID=$!

echo ""
echo "========================================="
echo "  Good Life Assistant 已启动"
echo "  前端: http://localhost:5173"
echo "  后端: http://localhost:8000"
echo "  API:  http://localhost:8000/docs"
echo "========================================="
echo ""

# Graceful shutdown
cleanup() {
    echo "[INFO] 正在关闭服务..."
    kill $FRONTEND_PID 2>/dev/null || true
    kill $BACKEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

wait
