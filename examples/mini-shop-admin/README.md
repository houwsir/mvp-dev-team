# mini-shop-admin

面向小型电商运营人员的**商品与订单一体化管理后台**，覆盖管理员登录、商品维护、库存与上下架管理、
订单查询、发货、取消及内部备注，构成一个可独立运行的最小运营闭环。

> 本目录由 **MVP 开发专家团**（LangGraph 多智能体工作流）根据一句话需求生成：
> 「我想做一个电商小程序后台，用来管理商品和订单」。
> 生成后由质量门驳回 2 轮，剩余缺陷已由人工修复（见文末「已知问题与修复记录」）。

## 技术栈

- 后端：Python 3.11+、FastAPI、SQLAlchemy 2.0、SQLite、Uvicorn
- 前端：React 18、TypeScript、Vite 5、React Router 6（**不引入任何 UI 库**，样式用原生 CSS 变量）
- 部署：Docker Compose、Nginx
- 测试：pytest（后端 28 个用例）

## 目录结构

```text
mini-shop-admin/
├── backend/
│   ├── app/                    # FastAPI 应用
│   │   ├── api/routes/         # 认证、商品、订单、健康检查路由
│   │   ├── repositories/       # 数据访问层
│   │   ├── services/           # 业务逻辑
│   │   ├── schemas/            # Pydantic 模型与公共枚举
│   │   ├── models.py           # SQLAlchemy 模型
│   │   ├── seed.py             # 幂等种子数据
│   │   └── main.py             # 应用入口
│   ├── tests/                  # pytest 用例
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/                    # React 管理后台（页面 / 组件 / API 客户端 / 样式令牌）
│   ├── package.json
│   └── vite.config.ts          # 开发代理：/api → http://localhost:8000
├── deploy/
│   ├── start.sh                # 本地一键启动（前后端一起拉起）
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── docker-compose.yml
│   └── nginx.conf
├── docs/                       # PRD / 设计规范 / 技术方案 / 测试报告 / 运行手册
├── Makefile
└── README.md
```

## 快速开始

### 方式一：一键启动（推荐）

```bash
bash deploy/start.sh
```

脚本会：创建后端虚拟环境 → 安装依赖 → 启动后端(8000) → 启动前端(5173)，并在结束时一并关闭。

### 方式二：手动启动

```bash
# 后端 → http://localhost:8000
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端 → http://localhost:5173
cd frontend
npm install
npm run dev
```

### 方式三：Docker Compose

```bash
make docker-up     # 等价于 docker compose -f deploy/docker-compose.yml up --build
make docker-down
```

打开 <http://localhost:5173> 进入管理后台，接口文档在 <http://localhost:8000/docs>。

### 登录账号

| 项 | 值 |
| --- | --- |
| 用户名 | `admin` |
| 密码 | `admin123456`（可用环境变量 `SEED_ADMIN_PASSWORD` 覆盖，建议部署前修改） |

> 首次启动会自动建表并注入种子数据（9 个商品、6 个订单，覆盖各订单状态）。
> 数据落在 `backend/mini-shop-admin.db`（Docker 部署时落在命名卷 `mini-shop-admin-sqlite-data`）。

## 常用命令

```bash
make install    # 安装前后端依赖
make dev        # 一键启动开发环境
make test       # 后端 pytest + 前端类型检查
make build      # 前端生产构建 + 后端字节码编译检查
make clean      # 清理虚拟环境、node_modules、dist 与缓存
make docker-up  # Docker Compose 启动
```

## 接口一览

所有业务接口统一挂在 `/api` 下，除 `/api/health` 与 `/api/auth/login` 外均需登录会话
（Cookie `admin_session`）。错误响应统一为 `{"detail": "...", "code": "..."}`。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查（含数据库连通性） |
| POST | `/api/auth/login` | 管理员登录 |
| POST | `/api/auth/logout` | 退出登录 |
| GET | `/api/auth/me` | 当前登录管理员 |
| GET | `/api/products` | 商品列表（分页 + 关键字 + 上下架筛选） |
| POST | `/api/products` | 新建商品 |
| GET | `/api/products/{product_id}` | 商品详情 |
| PUT | `/api/products/{product_id}` | 编辑商品 |
| PATCH | `/api/products/{product_id}/status` | 上架 / 下架 |
| PATCH | `/api/products/{product_id}/stock` | 调整库存 |
| GET | `/api/orders` | 订单列表（分页 + 订单号精确搜索 + 状态筛选） |
| GET | `/api/orders/{order_id}` | 订单详情（含商品明细、收货信息、状态时间线） |
| POST | `/api/orders/{order_id}/ship` | 发货 |
| POST | `/api/orders/{order_id}/cancel` | 取消订单 |
| PATCH | `/api/orders/{order_id}/internal-note` | 维护内部备注 |
| GET | `/api/stats/overview` | 看板统计（商品数、在售数、订单数、待发货数） |

`page_size` 只接受 `20` 或 `50`，其他取值返回 422。

## 已知问题与修复记录

质量门（测试工程师角色）共驳回 2 轮，最终 28 个用例中 25 个通过。以下是生成后**由人工修复**的缺陷：

| 缺陷 | 根因 | 修复 |
| --- | --- | --- |
| `GET /api/products`、`GET /api/orders` 带 `page_size` 时返回 422 | query 参数写成 `Literal[20, 50]`，而 query 值始终是字符串，FastAPI 不会套 int 转换 | 改为 `IntEnum PageSize`（`app/schemas/common.py`），保留「只能是 20/50」的约束 |
| 取消订单后 `status_history` 缺失最新记录 | 关系用 `selectinload` 预加载，`commit` 后会话未失效，读回命中 identity map 拿到旧对象 | 提交后补 `db.expire_all()`（发货 / 取消 / 备注三处） |
| `npm run build` 失败 | `vite.config.ts` 写了 Vitest 的 `test` 字段，但其不存在于 Vite 的 `UserConfig` 类型，且未引入 vitest | 移除该字段（本项目刻意保持零额外依赖） |
| Makefile 引用 `deploy/start.sh`、`deploy/Dockerfile.backend` 但文件不存在 | 运维工程师交付不完整 | 补齐两个文件 |
| Makefile 调用 `npm test`，但 package.json 无该脚本 | 文档承诺了未实现的能力 | Makefile 改为后端 pytest + 前端 `tsc -b`；README 同步修正 |

## 后续可扩展

- 商品分类、多规格 SKU、批量导入导出
- 订单退款 / 售后流程与操作审计
- 多管理员账号与角色权限
- 前端 E2E 测试（Playwright）与可视化回归
- 看板图表化与经营报表导出

## 许可

MIT
