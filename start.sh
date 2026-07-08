#!/bin/bash

# 获取当前脚本所在目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "🚀 Starting WeChat Binding Demo..."

# 运行后端
echo "👉 Starting Backend API (port 8000)..."
cd "$DIR/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd "$DIR"
python -m backend.main &
BACKEND_PID=$!

# 运行前端
echo "👉 Starting Frontend dev server (port 3000)..."
cd "$DIR/frontend"
npm install
npm run dev &
FRONTEND_PID=$!

# 处理退出信号
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT TERM EXIT

# 挂起脚本以保持后台任务运行
wait
