.PHONY: help install dev backend frontend test build clean

help:
	@echo "make install   安装前后端依赖"
	@echo "make dev       一键启动前后端（推荐，等价于 bash deploy/start.sh）"
	@echo "make backend   仅启动后端"
	@echo "make frontend  仅启动前端"
	@echo "make test      运行后端自动化测试"
	@echo "make build     构建前端静态产物"
	@echo "make clean     清理临时产物"

install:
	cd backend && python3 -m pip install -r requirements.txt
	cd frontend && npm install --no-audit --no-fund

dev:
	bash deploy/start.sh

backend:
	cd backend && python3 -m uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && python3 -m pytest -q

build:
	cd frontend && npm run build

clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/dist frontend/node_modules/.vite backend/.pytest_cache
