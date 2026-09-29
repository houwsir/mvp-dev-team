SHELL := /usr/bin/env bash

PYTHON ?= python3
VENV := .venv
VENV_PYTHON := $(VENV)/bin/python
BACKEND_DIR := backend
FRONTEND_DIR := frontend
COMPOSE_FILE := deploy/docker-compose.yml

.PHONY: install dev test build clean docker-up docker-down

install:
	@test -f "$(BACKEND_DIR)/requirements.txt" || { echo "缺少 $(BACKEND_DIR)/requirements.txt"; exit 1; }
	@test -f "$(FRONTEND_DIR)/package.json" || { echo "缺少 $(FRONTEND_DIR)/package.json"; exit 1; }
	@command -v "$(PYTHON)" >/dev/null 2>&1 || { echo "未找到 $(PYTHON)，请安装 Python 3.11+"; exit 1; }
	@command -v npm >/dev/null 2>&1 || { echo "未找到 npm，请安装 Node.js 18+"; exit 1; }
	@test -x "$(VENV_PYTHON)" || "$(PYTHON)" -m venv "$(VENV)"
	@"$(VENV_PYTHON)" -m pip install --disable-pip-version-check --quiet --upgrade pip
	@"$(VENV_PYTHON)" -m pip install --disable-pip-version-check --quiet -r "$(BACKEND_DIR)/requirements.txt"
	@cd "$(FRONTEND_DIR)" && npm install --no-audit --no-fund

dev:
	@bash deploy/start.sh

test: install
	@echo "==> 后端单元测试（pytest）"
	@cd "$(BACKEND_DIR)" && "../$(VENV_PYTHON)" -m pytest -p no:cacheprovider
	@echo "==> 前端类型检查（tsc -b）"
	@cd "$(FRONTEND_DIR)" && npx --no-install tsc -b

build: install
	@"$(VENV_PYTHON)" -m compileall -q "$(BACKEND_DIR)/app"
	@cd "$(FRONTEND_DIR)" && npm run build

clean:
	@rm -rf "$(VENV)"
	@rm -rf "$(FRONTEND_DIR)/node_modules" "$(FRONTEND_DIR)/dist"
	@rm -rf "$(BACKEND_DIR)/.pytest_cache" "$(FRONTEND_DIR)/.pytest_cache"
	@find "$(BACKEND_DIR)" "$(FRONTEND_DIR)" \
		-type d \( -name __pycache__ -o -name .vite -o -name coverage \) \
		-prune -exec rm -rf {} +
	@find "$(BACKEND_DIR)" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

docker-up:
	@docker compose -f "$(COMPOSE_FILE)" up --build

docker-down:
	@docker compose -f "$(COMPOSE_FILE)" down
