#!/usr/bin/env bash
# 一键本地启动：后端 uvicorn + 前端 vite。
# 用法：bash deploy/start.sh   （可用 Ctrl+C 同时停止两端）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cleanup() {
  if [ -n "${BACK_PID:-}" ]; then kill "$BACK_PID" 2>/dev/null || true; fi
  if [ -n "${FRONT_PID:-}" ]; then kill "$FRONT_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

port_busy() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -i ":$port" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi
  return 1
}

echo "▶ 环境检查"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || { echo "✗ 未找到 $PYTHON_BIN"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "✗ 未找到 npm"; exit 1; }
for p in "$BACKEND_PORT" "$FRONTEND_PORT"; do
  if port_busy "$p"; then
    echo "  ⚠️  端口 $p 已被占用，请先释放或改用 BACKEND_PORT / FRONTEND_PORT 覆盖"
    exit 1
  fi
done

echo "▶ 准备后端依赖"
cd "$ROOT/backend"
if [ ! -d .venv ]; then
  "$PYTHON_BIN" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -q --disable-pip-version-check -r requirements.txt

echo "▶ 启动后端 -> http://127.0.0.1:${BACKEND_PORT}"
python -m uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT" &
BACK_PID=$!

echo "▶ 准备前端依赖"
cd "$ROOT/frontend"
if [ ! -d node_modules ]; then
  npm install --no-audit --no-fund
fi

echo "▶ 启动前端 -> http://127.0.0.1:${FRONTEND_PORT}"
npm run dev -- --port "$FRONTEND_PORT" --host 127.0.0.1 &
FRONT_PID=$!

echo
echo "✅ 后端接口文档：http://127.0.0.1:${BACKEND_PORT}/docs"
echo "✅ 前端页面：    http://127.0.0.1:${FRONTEND_PORT}"
echo "   按 Ctrl+C 同时停止"
echo

wait
