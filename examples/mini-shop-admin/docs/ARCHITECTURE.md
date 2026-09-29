# 技术方案与 API 契约

## 1. 方案概述

mini-shop-admin 采用前后端分离的单体架构。React 管理后台通过 /api REST JSON 接口访问 FastAPI 服务，FastAPI 使用 SQLAlchemy ORM 持久化到单文件 SQLite。认证采用服务端会话：登录成功后生成高熵随机令牌，仅将 SHA-256 哈希写入 admin_session，原始令牌通过 HttpOnly、SameSite=Strict Cookie 返回；默认有效期 8 小时，退出时撤销会话。除登录和健康检查外，所有接口均要求有效会话。密码使用 Argon2id 哈希。金额在数据库中使用 NUMERIC(10,2)，API 中统一返回两位小数字符串；时间以 UTC 保存并返回 ISO 8601 UTC 字符串。订单状态变更、物流记录和状态历史在同一数据库事务内完成，并通过带当前状态条件的 UPDATE 防止重复发货或并发非法流转。所有错误统一返回 {"detail":"面向用户的错误描述","code":"稳定错误码"}。

## 2. 技术选型

| 层次 | 选型 |
| --- | --- |
| backend | Python 3.11+；FastAPI 0.115；Uvicorn；SQLAlchemy 2.0 ORM；Pydantic v2；pwdlib[argon2]；分层结构为 router → service → repository/model |
| frontend | React 18；TypeScript；Vite 5；react-router-dom 6；原生 CSS 与 CSS Variables；浏览器 fetch 封装 API 客户端并启用 credentials |
| database | SQLite 单文件；SQLAlchemy 自动建表；外键约束开启；启动时幂等注入管理员、商品、订单及状态历史种子数据；金额使用 NUMERIC(10,2)，枚举使用 VARCHAR + CHECK |
| test | pytest；FastAPI TestClient/httpx；临时 SQLite 数据库；后端覆盖认证、校验、状态机、事务回滚和字段隔离；前端使用 Vitest + React Testing Library；关键流程使用 Playwright 做 1280px 桌面端验收 |
| deploy | Docker Compose；Nginx 提供前端静态文件并反向代理 /api；Uvicorn 单进程运行 FastAPI；SQLite 文件挂载到持久化卷；提供 /api/health 健康检查和环境变量模板 |

## 3. 数据模型

### 管理员账号 → 表 `admin_user`

- `id: INTEGER PRIMARY KEY AUTOINCREMENT`
- `username: VARCHAR(64) NOT NULL UNIQUE`
- `password_hash: VARCHAR(255) NOT NULL`
- `display_name: VARCHAR(64) NOT NULL`
- `is_active: BOOLEAN NOT NULL DEFAULT TRUE`
- `last_login_at: DATETIME NULL`
- `created_at: DATETIME NOT NULL`
- `updated_at: DATETIME NOT NULL`

### 管理员会话 → 表 `admin_session`

- `id: VARCHAR(36) PRIMARY KEY`
- `admin_user_id: INTEGER NOT NULL REFERENCES admin_user(id) ON DELETE CASCADE`
- `token_hash: VARCHAR(64) NOT NULL UNIQUE`
- `expires_at: DATETIME NOT NULL`
- `revoked_at: DATETIME NULL`
- `created_at: DATETIME NOT NULL`
- `INDEX ix_admin_session_admin_user_id: (admin_user_id)`
- `INDEX ix_admin_session_expires_at: (expires_at)`

### 商品 → 表 `product`

- `id: INTEGER PRIMARY KEY AUTOINCREMENT`
- `name: VARCHAR(200) NOT NULL`
- `main_image_url: VARCHAR(2048) NOT NULL`
- `price: NUMERIC(10,2) NOT NULL CHECK (price > 0)`
- `stock: INTEGER NOT NULL CHECK (stock >= 0)`
- `description: TEXT NULL`
- `status: VARCHAR(16) NOT NULL DEFAULT 'inactive' CHECK (status IN ('active','inactive'))`
- `created_by: INTEGER NOT NULL REFERENCES admin_user(id)`
- `updated_by: INTEGER NOT NULL REFERENCES admin_user(id)`
- `created_at: DATETIME NOT NULL`
- `updated_at: DATETIME NOT NULL`
- `CHECK ck_product_active_stock: status = 'inactive' OR stock > 0`
- `INDEX ix_product_name: (name)`
- `INDEX ix_product_status_updated_at: (status, updated_at)`

### 订单 → 表 `shop_order`

- `id: INTEGER PRIMARY KEY AUTOINCREMENT`
- `order_no: VARCHAR(32) NOT NULL UNIQUE`
- `buyer_id: VARCHAR(64) NOT NULL`
- `buyer_name: VARCHAR(100) NOT NULL`
- `status: VARCHAR(32) NOT NULL CHECK (status IN ('pending_payment','pending_shipment','shipped','completed','cancelled'))`
- `items_amount: NUMERIC(10,2) NOT NULL CHECK (items_amount >= 0)`
- `shipping_fee: NUMERIC(10,2) NOT NULL CHECK (shipping_fee >= 0)`
- `payable_amount: NUMERIC(10,2) NOT NULL CHECK (payable_amount >= 0)`
- `receiver_name: VARCHAR(100) NOT NULL`
- `receiver_phone: VARCHAR(32) NOT NULL`
- `receiver_province: VARCHAR(100) NOT NULL`
- `receiver_city: VARCHAR(100) NOT NULL`
- `receiver_district: VARCHAR(100) NOT NULL`
- `receiver_address: VARCHAR(500) NOT NULL`
- `buyer_message: VARCHAR(500) NULL`
- `internal_note: VARCHAR(1000) NULL`
- `placed_at: DATETIME NOT NULL`
- `created_at: DATETIME NOT NULL`
- `updated_at: DATETIME NOT NULL`
- `CHECK ck_shop_order_amount: payable_amount = items_amount + shipping_fee`
- `INDEX ix_shop_order_status_placed_at: (status, placed_at)`

### 订单商品明细 → 表 `order_item`

- `id: INTEGER PRIMARY KEY AUTOINCREMENT`
- `order_id: INTEGER NOT NULL REFERENCES shop_order(id) ON DELETE CASCADE`
- `product_id: INTEGER NOT NULL REFERENCES product(id)`
- `product_name: VARCHAR(200) NOT NULL`
- `product_image_url: VARCHAR(2048) NOT NULL`
- `unit_price: NUMERIC(10,2) NOT NULL CHECK (unit_price > 0)`
- `quantity: INTEGER NOT NULL CHECK (quantity > 0)`
- `line_amount: NUMERIC(10,2) NOT NULL CHECK (line_amount >= 0)`
- `created_at: DATETIME NOT NULL`
- `INDEX ix_order_item_order_id: (order_id)`

### 订单物流 → 表 `order_shipment`

- `id: INTEGER PRIMARY KEY AUTOINCREMENT`
- `order_id: INTEGER NOT NULL UNIQUE REFERENCES shop_order(id) ON DELETE CASCADE`
- `logistics_company: VARCHAR(100) NOT NULL`
- `tracking_no: VARCHAR(100) NOT NULL`
- `shipped_by: INTEGER NOT NULL REFERENCES admin_user(id)`
- `shipped_at: DATETIME NOT NULL`
- `created_at: DATETIME NOT NULL`
- `updated_at: DATETIME NOT NULL`

### 订单状态历史 → 表 `order_status_history`

- `id: INTEGER PRIMARY KEY AUTOINCREMENT`
- `order_id: INTEGER NOT NULL REFERENCES shop_order(id) ON DELETE CASCADE`
- `from_status: VARCHAR(32) NULL CHECK (from_status IS NULL OR from_status IN ('pending_payment','pending_shipment','shipped','completed','cancelled'))`
- `to_status: VARCHAR(32) NOT NULL CHECK (to_status IN ('pending_payment','pending_shipment','shipped','completed','cancelled'))`
- `event_type: VARCHAR(32) NOT NULL CHECK (event_type IN ('created','payment_confirmed','shipped','completed','cancelled'))`
- `operator_type: VARCHAR(16) NOT NULL CHECK (operator_type IN ('system','admin'))`
- `operator_admin_id: INTEGER NULL REFERENCES admin_user(id)`
- `event_note: VARCHAR(500) NULL`
- `created_at: DATETIME NOT NULL`
- `INDEX ix_order_status_history_order_time: (order_id, created_at)`

## 4. API 契约

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 服务健康检查 |
| POST | `/api/auth/login` | 管理员登录并创建会话 |
| POST | `/api/auth/logout` | 撤销当前管理员会话并退出 |
| GET | `/api/auth/me` | 获取当前登录管理员 |
| GET | `/api/products` | 分页查询商品列表 |
| POST | `/api/products` | 创建商品 |
| GET | `/api/products/{product_id}` | 获取商品详情 |
| PUT | `/api/products/{product_id}` | 完整更新商品基础资料、价格和库存 |
| PATCH | `/api/products/{product_id}/stock` | 调整商品库存 |
| PATCH | `/api/products/{product_id}/status` | 上架或下架商品 |
| GET | `/api/orders` | 分页查询订单列表 |
| GET | `/api/orders/{order_id}` | 获取订单完整详情 |
| POST | `/api/orders/{order_id}/ship` | 为待发货订单录入物流并发货 |
| POST | `/api/orders/{order_id}/cancel` | 取消待付款或待发货订单 |
| PATCH | `/api/orders/{order_id}/internal-note` | 新增、修改或清空订单内部备注 |

### `GET /api/health`

服务健康检查

请求：

```json
无请求参数，无需鉴权。
```

响应：

```json
200 application/json：{"status":"ok"}。
```

### `POST /api/auth/login`

管理员登录并创建会话

请求：

```json
JSON：{"username":"admin","password":"string"}。username 去除首尾空格后必填且最长 64 字符；password 必填且最长 128 字符。
```

响应：

```json
200 application/json，并设置 admin_session HttpOnly、SameSite=Strict Cookie：{"admin":{"id":1,"username":"admin","display_name":"商城管理员"},"expires_at":"2025-01-01T08:00:00Z"}。
```

### `POST /api/auth/logout`

撤销当前管理员会话并退出

请求：

```json
无请求体；从 admin_session Cookie 读取当前会话。
```

响应：

```json
200 application/json，清除 admin_session Cookie：{"success":true}。会话不存在或已失效时仍幂等返回成功。
```

### `GET /api/auth/me`

获取当前登录管理员

请求：

```json
无请求参数；要求有效 admin_session Cookie。
```

响应：

```json
200 application/json：{"id":1,"username":"admin","display_name":"商城管理员"}。
```

### `GET /api/products`

分页查询商品列表

请求：

```json
Query：page=1（整数，>=1）；page_size=20（仅允许 20 或 50）；keyword 可选，去除首尾空格后按 name 模糊匹配；status 可选，仅 active 或 inactive。默认按 updated_at DESC、id DESC 排序。
```

响应：

```json
200 application/json：{"items":[{"id":1,"name":"商品名称","main_image_url":"https://example.com/a.jpg","price":"99.00","stock":10,"description":"描述或 null","status":"active","created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T01:00:00Z"}],"page":1,"page_size":20,"total":1,"total_pages":1}。无匹配数据时 items=[]、total=0、total_pages=0。
```

### `POST /api/products`

创建商品

请求：

```json
JSON：{"name":"商品名称","main_image_url":"https://example.com/a.jpg","price":"99.00","stock":10,"description":"可选描述"}。name 去除首尾空格后长度 1..200；main_image_url 必须为 http/https URL 且最长 2048；price 大于 0、最多两位小数且不超过 99999999.99；stock 为 >=0 的整数；description 可为 null 或字符串。status 不接受客户端传入，新商品固定为 inactive。
```

响应：

```json
201 application/json：{"id":1,"name":"商品名称","main_image_url":"https://example.com/a.jpg","price":"99.00","stock":10,"description":"可选描述","status":"inactive","created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z"}。
```

### `GET /api/products/{product_id}`

获取商品详情

请求：

```json
Path：product_id 为正整数。
```

响应：

```json
200 application/json：{"id":1,"name":"商品名称","main_image_url":"https://example.com/a.jpg","price":"99.00","stock":10,"description":"描述或 null","status":"active","created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T01:00:00Z"}。
```

### `PUT /api/products/{product_id}`

完整更新商品基础资料、价格和库存

请求：

```json
Path：product_id 为正整数。JSON：{"name":"商品名称","main_image_url":"https://example.com/a.jpg","price":"99.00","stock":10,"description":"可选描述"}。校验规则与创建一致。不得通过本接口直接传 status；若已上架商品的 stock 更新为 0，服务端在同一事务中自动将 status 改为 inactive。
```

响应：

```json
200 application/json：返回更新后的完整商品对象，字段与 GET /api/products/{product_id} 一致。
```

### `PATCH /api/products/{product_id}/stock`

调整商品库存

请求：

```json
Path：product_id 为正整数。JSON：{"stock":20}；stock 必须为 >=0 的整数。若 active 商品调整为 0，服务端自动下架。
```

响应：

```json
200 application/json：返回更新后的完整商品对象，字段与 GET /api/products/{product_id} 一致。
```

### `PATCH /api/products/{product_id}/status`

上架或下架商品

请求：

```json
Path：product_id 为正整数。JSON：{"status":"active"} 或 {"status":"inactive"}。设置 active 时商品当前库存必须大于 0；重复设置为当前状态按幂等成功处理。
```

响应：

```json
200 application/json：返回更新后的完整商品对象，字段与 GET /api/products/{product_id} 一致。
```

### `GET /api/orders`

分页查询订单列表

请求：

```json
Query：page=1（整数，>=1）；page_size=20（仅允许 20 或 50）；order_no 可选，去除首尾空格后按完整订单号精确匹配；status 可选，仅允许 pending_payment、pending_shipment、shipped、completed、cancelled。默认按 placed_at DESC、id DESC 排序。
```

响应：

```json
200 application/json：{"items":[{"id":1,"order_no":"202501010001","placed_at":"2025-01-01T00:00:00Z","buyer_name":"张三","payable_amount":"109.00","status":"pending_shipment"}],"page":1,"page_size":20,"total":1,"total_pages":1}。无匹配数据时 items=[]、total=0、total_pages=0。
```

### `GET /api/orders/{order_id}`

获取订单完整详情

请求：

```json
Path：order_id 为正整数。
```

响应：

```json
200 application/json：{"id":1,"order_no":"202501010001","buyer_id":"buyer-1","buyer_name":"张三","status":"pending_shipment","items_amount":"99.00","shipping_fee":"10.00","payable_amount":"109.00","receiver":{"name":"张三","phone":"13800000000","province":"广东省","city":"深圳市","district":"南山区","address":"科技园 1 号"},"buyer_message":"尽快发货或 null","internal_note":"后台备注或 null","placed_at":"2025-01-01T00:00:00Z","created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z","items":[{"id":1,"product_id":1,"product_name":"下单商品快照","product_image_url":"https://example.com/a.jpg","unit_price":"99.00","quantity":1,"line_amount":"99.00"}],"shipment":null,"status_history":[{"id":1,"from_status":null,"to_status":"pending_payment","event_type":"created","operator_type":"system","operator_admin_id":null,"operator_display_name":null,"event_note":null,"created_at":"2025-01-01T00:00:00Z"}]}。status_history 按 created_at ASC、id ASC 排序；shipment 非空时包含 logistics_company、tracking_no、shipped_by、shipped_by_display_name、shipped_at。
```

### `POST /api/orders/{order_id}/ship`

为待发货订单录入物流并发货

请求：

```json
Path：order_id 为正整数。JSON：{"logistics_company":"顺丰速运","tracking_no":"SF123456789"}。两个字段去除首尾空格后均不能为空，且分别最长 100 字符。仅 pending_shipment 状态允许操作。
```

响应：

```json
200 application/json：返回更新后的完整订单详情，结构与 GET /api/orders/{order_id} 一致；status 为 shipped，shipment 非空，并新增 event_type=shipped、operator_type=admin 的状态记录。
```

### `POST /api/orders/{order_id}/cancel`

取消待付款或待发货订单

请求：

```json
Path：order_id 为正整数。JSON：{}。仅 pending_payment 或 pending_shipment 状态允许取消；前端负责展示确认对话框，服务端再次校验当前状态。
```

响应：

```json
200 application/json：返回更新后的完整订单详情，结构与 GET /api/orders/{order_id} 一致；status 为 cancelled，并新增 event_type=cancelled、operator_type=admin 的状态记录。
```

### `PATCH /api/orders/{order_id}/internal-note`

新增、修改或清空订单内部备注

请求：

```json
Path：order_id 为正整数。JSON：{"internal_note":"仅后台可见的备注"}。internal_note 接受字符串或 null，最长 1000 字符；空字符串规范化为 null。该字段仅存在于鉴权管理接口，不写入 buyer_message 或 order_status_history。
```

响应：

```json
200 application/json：返回更新后的完整订单详情，结构与 GET /api/orders/{order_id} 一致。
```

## 5. 目录与交付清单

- `backend/pyproject.toml：声明 Python 3.11、FastAPI、SQLAlchemy、Argon2、pytest 等依赖与工具配置。`
- `backend/.env.example：定义 DATABASE_URL、SESSION_TTL_HOURS、SESSION_COOKIE_SECURE、SEED_ADMIN_USERNAME、SEED_ADMIN_PASSWORD 等环境变量。`
- `backend/app/main.py：创建 FastAPI 应用、注册中间件和 /api 路由，并执行启动初始化。`
- `backend/app/config.py：使用 Pydantic Settings 加载和校验运行配置。`
- `backend/app/database.py：创建 SQLite Engine、Session 工厂，启用 foreign_keys 和 WAL，并提供数据库依赖。`
- `backend/app/models.py：定义全部 SQLAlchemy 2.0 ORM 模型、约束、索引和关联关系。`
- `backend/app/schemas/common.py：定义统一错误体、分页元数据和共享枚举。`
- `backend/app/schemas/auth.py：定义登录请求、管理员响应和会话响应模型。`
- `backend/app/schemas/product.py：定义商品创建、更新、库存、状态和响应模型。`
- `backend/app/schemas/order.py：定义订单列表、详情、物流、取消、备注和状态历史模型。`
- `backend/app/api/dependencies.py：解析会话 Cookie、校验过期与账号状态并注入当前管理员。`
- `backend/app/api/error_handlers.py：将业务异常、请求校验异常和未处理异常映射为统一 {detail, code} 响应。`
- `backend/app/api/routes/auth.py：实现登录、退出和当前管理员接口。`
- `backend/app/api/routes/products.py：实现商品列表、创建、详情、编辑、库存和上下架接口。`
- `backend/app/api/routes/orders.py：实现订单列表、详情、发货、取消和内部备注接口。`
- `backend/app/api/routes/health.py：实现应用与数据库健康检查。`
- `backend/app/services/auth_service.py：处理 Argon2 密码验证、令牌生成、哈希、会话创建与撤销。`
- `backend/app/services/product_service.py：封装商品校验、写入、零库存自动下架和审计管理员逻辑。`
- `backend/app/services/order_service.py：封装订单状态机、条件更新、物流与状态历史原子事务。`
- `backend/app/repositories/product_repository.py：封装商品查询、分页和持久化操作。`
- `backend/app/repositories/order_repository.py：封装订单聚合查询、精确搜索和状态条件更新。`
- `backend/app/seed.py：幂等创建初始管理员、示例商品、示例订单和状态记录。`
- `backend/tests/conftest.py：提供隔离数据库、测试客户端、登录会话和种子数据夹具。`
- `backend/tests/test_auth.py：覆盖正确登录、错误密码、禁用账号、过期会话和退出撤销。`
- `backend/tests/test_products.py：覆盖商品分页、搜索、校验、编辑、库存和上下架规则。`
- `backend/tests/test_orders.py：覆盖订单查询、详情快照、发货、取消、并发状态冲突和备注持久化。`
- `backend/tests/test_consumer_field_isolation.py：验证 internal_note 不进入任何消费者数据映射或非管理响应。`
- `backend/Dockerfile：构建并运行 FastAPI/Uvicorn 后端镜像。`
- `frontend/package.json：声明 React 18、TypeScript、Vite 5、react-router-dom 6 和测试依赖。`
- `frontend/vite.config.ts：配置 React 插件、开发服务器和 /api 代理。`
- `frontend/src/main.tsx：挂载 React 应用并初始化路由。`
- `frontend/src/App.tsx：定义登录页、受保护管理路由和后台布局。`
- `frontend/src/api/client.ts：封装 fetch、credentials、JSON 解析、统一错误和 401 跳转。`
- `frontend/src/api/auth.ts：实现登录、退出和当前管理员 API 调用。`
- `frontend/src/api/products.ts：实现商品查询、创建、更新、库存与状态 API 调用。`
- `frontend/src/api/orders.ts：实现订单查询、详情、发货、取消和备注 API 调用。`
- `frontend/src/types/api.ts：声明统一错误、分页响应和共享 API 类型。`
- `frontend/src/types/product.ts：声明与契约一致的商品请求及响应类型。`
- `frontend/src/types/order.ts：声明订单、明细、收货信息、物流和状态历史类型。`
- `frontend/src/auth/AuthProvider.tsx：维护当前管理员、启动会话检查和退出状态。`
- `frontend/src/auth/ProtectedRoute.tsx：保护管理路由并将未登录用户跳转到 /login。`
- `frontend/src/layout/AdminLayout.tsx：提供商品、订单导航和退出入口。`
- `frontend/src/pages/LoginPage.tsx：实现管理员登录表单、字段校验和错误反馈。`
- `frontend/src/pages/ProductListPage.tsx：实现商品分页、搜索、筛选、库存调整和上下架。`
- `frontend/src/pages/ProductFormPage.tsx：复用实现商品创建与编辑、图片预览和字段校验。`
- `frontend/src/pages/OrderListPage.tsx：实现订单号精确搜索、状态筛选和分页列表。`
- `frontend/src/pages/OrderDetailPage.tsx：展示订单聚合详情并实现发货、取消和内部备注。`
- `frontend/src/components/Pagination.tsx：实现固定 20/50 页大小和页码切换。`
- `frontend/src/components/ConfirmDialog.tsx：实现取消订单等危险操作确认。`
- `frontend/src/components/ShipmentDialog.tsx：实现物流公司与运单号录入及校验。`
- `frontend/src/components/StockDialog.tsx：实现非负整数库存调整。`
- `frontend/src/components/StatusBadge.tsx：统一展示商品与订单状态。`
- `frontend/src/styles/tokens.css：定义颜色、间距、排版、边框和状态色 CSS Variables。`
- `frontend/src/styles/global.css：定义 1280px 以上桌面布局、表格、表单和反馈状态。`
- `frontend/src/test/pages.test.tsx：覆盖登录、商品表单、失败回滚和订单操作条件渲染。`
- `frontend/e2e/admin-flow.spec.ts：覆盖登录、商品维护、订单发货、取消、备注和退出核心流程。`
- `frontend/Dockerfile：构建 Vite 静态资源并交由 Nginx 服务。`
- `frontend/nginx.conf：提供 SPA history fallback，并将 /api 反向代理到后端。`
- `docker-compose.yml：编排前端、后端、健康检查和 SQLite 持久化卷。`
- `.env.example：提供容器部署所需的非敏感环境变量模板。`
- `README.md：记录本地启动、种子管理员、测试、备份和部署操作。`

## 6. 风险

- SQLite 写操作为单写者模型；商品和订单操作量较小时适合 MVP，但并发写入增加后可能出现锁等待。需启用 WAL、busy_timeout、短事务和单 Uvicorn 进程，规模增长后迁移 PostgreSQL。
- 主图仅保存外部 URL，外部资源失效、防盗链或混合内容会导致后台图片无法显示；前端需提供加载失败占位，正式版本应接入受控对象存储和上传服务。
- 启动时自动建表适合 MVP，但不能安全处理后续字段变更；首次发布后应引入 Alembic 版本化迁移，并在升级前备份 SQLite 文件。
