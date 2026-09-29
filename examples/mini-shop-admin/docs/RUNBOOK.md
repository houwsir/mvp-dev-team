# 运行手册

## 1. 目录结构

- `Makefile`
- `README.md`
- `frontend/index.html`
- `frontend/package.json`
- `frontend/tsconfig.app.json`
- `frontend/tsconfig.json`
- `frontend/tsconfig.node.json`
- `frontend/vite.config.ts`
- `frontend/e2e/admin-flow.spec.ts`
- `frontend/src/App.tsx`
- `frontend/src/main.tsx`
- `frontend/src/vite-env.d.ts`
- `frontend/src/types/api.ts`
- `frontend/src/types/order.ts`
- `frontend/src/types/product.ts`
- `frontend/src/test/pages.test.tsx`
- `frontend/src/test/setup.ts`
- `frontend/src/auth/AuthProvider.tsx`
- `frontend/src/auth/ProtectedRoute.tsx`
- `frontend/src/layout/AdminLayout.tsx`
- `frontend/src/utils/format.ts`
- `frontend/src/styles/global.css`
- `frontend/src/styles/tokens.css`
- `frontend/src/components/ConfirmDialog.tsx`
- `frontend/src/components/Pagination.tsx`
- `frontend/src/components/ProductImage.tsx`
- `frontend/src/components/ShipmentDialog.tsx`
- `frontend/src/components/StatusBadge.tsx`
- `frontend/src/components/StockDialog.tsx`
- `frontend/src/components/ThemeToggle.tsx`
- `frontend/src/components/Toast.tsx`
- `frontend/src/hooks/useTheme.ts`
- `frontend/src/api/auth.ts`
- `frontend/src/api/client.ts`
- `frontend/src/api/orders.ts`
- `frontend/src/api/products.ts`
- `frontend/src/pages/LoginPage.tsx`
- `frontend/src/pages/OrderDetailPage.tsx`
- `frontend/src/pages/OrderListPage.tsx`
- `frontend/src/pages/ProductFormPage.tsx`
- `frontend/src/pages/ProductListPage.tsx`
- `deploy/Dockerfile.frontend`
- `deploy/docker-compose.yml`
- `deploy/nginx.conf`
- `backend/.env.example`
- `backend/Dockerfile`
- `backend/pyproject.toml`
- `backend/requirements.txt`
- `backend/app/__init__.py`
- `backend/app/config.py`
- `backend/app/database.py`
- `backend/app/main.py`
- `backend/app/models.py`
- `backend/app/seed.py`
- `backend/app/repositories/__init__.py`
- `backend/app/repositories/order_repository.py`
- `backend/app/repositories/product_repository.py`
- `backend/app/schemas/__init__.py`
- `backend/app/schemas/auth.py`
- `backend/app/schemas/common.py`
- `backend/app/schemas/order.py`
- `backend/app/schemas/product.py`
- `backend/app/api/__init__.py`
- `backend/app/api/dependencies.py`
- `backend/app/api/error_handlers.py`
- `backend/app/api/routes/__init__.py`
- `backend/app/api/routes/auth.py`
- `backend/app/api/routes/health.py`
- `backend/app/api/routes/orders.py`
- `backend/app/api/routes/products.py`
- `backend/app/services/__init__.py`
- `backend/app/services/auth_service.py`
- `backend/app/services/order_service.py`
- `backend/app/services/product_service.py`
- `backend/tests/__init__.py`
- `backend/tests/conftest.py`
- `backend/tests/test.db-shm`
- `backend/tests/test.db-wal`
- `backend/tests/test_auth.py`
- `backend/tests/test_consumer_field_isolation.py`

## 2. 一键启动（推荐）

```bash
cd /Users/hw/passer/workbuddy-ws/工作流/mvp-dev-team/generated/mini-shop-admin
bash deploy/start.sh
```

## 3. 手动启动

```bash
# 后端（端口 8000）
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端（端口 5173）
cd frontend && npm install && npm run dev
```

## 4. 质量门结论

- 是否放行：❌ 否
- 测试轮次：2
- 概述：质量门不通过：pytest 共 28 项，25 项通过、3 项失败；同时静态体检存在 1 项 frontend high 缺陷。订单与商品查询、订单取消状态历史等后端主流程存在问题，前端商品新建与编辑路由也被静态体检判定为缺失。
