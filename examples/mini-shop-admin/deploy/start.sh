#!/usr/bin/env bash
# 本地一键启动：后端（8000） + 前端（5173）
#
# 用法：
#   bash deploy/start.sh              # 正常启动
#   SEED_ADMIN_PASSWORD=xxx bash deploy/start.sh
#
# Ctrl-C 会同时结束前后端进程。
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"
VENV_DIR="${ROOT_DIR}/backend/.venv"

PYTHON_BIN="${PYTHON_BIN:-python3}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

export SEED_ADMIN_USERNAME="${SEED_ADMIN_USERNAME:-admin}"
export SEED_ADMIN_PASSWORD="${SEED_ADMIN_PASSWORD:-admin123456}"
export DATABASE_URL="${DATABASE_URL:-sqlite:///${BACKEND_DIR}/mini-shop-admin.db}"

info()  { printf '\033[36m▶ %s\033[0m\n' "$1"; }
warn()  { printf '\033[33m⚠ %s\033[0m\n' "$1"; }
fail()  { printf '\033[31m✖ %s\033[0m\n' "$1" >&2; exit 1; }

command -v "${PYTHON_BIN}" >/dev/null 2>&1 || fail "未找到 ${PYTHON_BIN}，请先安装 Python 3.11+"
command -v npm >/dev/null 2>&1 || fail "未找到 npm，请先安装 Node.js 18+"

# ---------- 端口占用检查 ----------
check_port() {
  local port="$1" name="$2"
  if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
    fail "${name} 端口 ${port} 已被占用，请先释放，或改用 ${name^^}_PORT=<其他端口> 启动"
  fi
}
check_port "${BACKEND_PORT}" backend
check_port "${FRONTEND_PORT}" frontend

# ---------- 后端 ----------
info "准备后端虚拟环境 ${VENV_DIR}"
if [ ! -x "${VENV_DIR}/bin/python" ]; then
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi
"${VENV_DIR}/bin/python" -m pip install --disable-pip-version-check --quiet --upgrade pip
info "安装后端依赖（requirements.txt）"
"${VENV_DIR}/bin/python" -m pip install --disable-pip-version-check --quiet -r "${BACKEND_DIR}/requirements.txt"

# ---------- 前端 ----------
if [ ! -d "${FRONTEND_DIR}/node_modules" ]; then
  info "安装前端依赖（首次会比较慢）"
  ( cd "${FRONTEND_DIR}" && npm install --no-audit --no-fund )
else
  info "前端依赖已存在，跳过安装"
fi

# ---------- 启动 ----------
PIDS=()
cleanup() {
  warn "正在停止服务…"
  for pid in "${PIDS[@]:-}"; do
    kill "${pid}" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

info "启动后端 → http://localhost:${BACKEND_PORT}"
( cd "${BACKEND_DIR}" && "${VENV_DIR}/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port "${BACKEND_PORT}" --reload ) &
PIDS+=("$!")

sleep 2

info "启动前端 → http://localhost:${FRONTEND_PORT}"
( cd "${FRONTEND_DIR}" && npm run dev -- --port "${FRONTEND_PORT}" ) &
PIDS+=("$!")

printf '\n'
info "已启动。管理后台：http://localhost:${FRONTEND_PORT}　接口文档：http://localhost:${BACKEND_PORT}/docs"
info "登录账号：${SEED_ADMIN_USERNAME} / ${SEED_ADMIN_PASSWORD}"
printf '\n'

wait
