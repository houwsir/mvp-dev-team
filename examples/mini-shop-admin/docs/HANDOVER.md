# mini-shop-admin 交付说明

## 产品定位

`mini-shop-admin` 是面向小程序商城店主及电商运营人员的商品、订单一体化管理后台，目标是覆盖商品维护、上下架、订单查询、发货、取消和内部备注等最小运营闭环。

本次交付不包含消费者端、支付退款、多规格 SKU、营销体系、多角色权限、复杂库存、物流轨迹同步、数据报表及批量操作。

## 本次实现

现有交付文件覆盖以下内容：

- 管理员登录、退出与会话鉴权。
- 商品分页、关键词搜索、状态筛选、创建、编辑、上下架和库存调整。
- 商品名称、主图、售价、库存等字段的服务端校验。
- 零库存商品禁止上架。
- 订单分页、完整订单号搜索、状态筛选和订单详情。
- 待发货订单录入物流公司、运单号并发货。
- 待付款或待发货订单取消。
- 订单内部备注与状态记录。
- 消费者字段隔离测试。
- React 管理后台页面，包括登录、商品列表、商品表单、订单列表和订单详情。
- Docker Compose、前后端 Dockerfile、Nginx 配置和运行文档。
- PRD、设计规范、系统架构、项目计划、运行手册及两轮测试报告。
- 后端 pytest 测试和前端页面测试、Playwright 端到端用例。

## 目录结构

项目共交付 **88 个文件**，其中后端文件 **37 个**、前端文件 **39 个**。

```text
mini-shop-admin/
├── Makefile
├── README.md
├── backend/                    # FastAPI 后端、数据模型、服务与 pytest 测试
│   ├── app/
│   │   ├── api/routes/         # 登录、健康检查、商品和订单接口
│   │   ├── repositories/       # 商品与订单数据访问
│   │   ├── schemas/            # API 请求与响应模型
│   │   └── services/           # 认证、商品与订单业务逻辑
│   ├── tests/                  # 后端自动化测试
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/                   # React/Vite 管理后台
│   ├── e2e/                    # Playwright 管理流程用例
│   ├── src/
│   │   ├── api/                # 后端 API 客户端
│   │   ├── auth/               # 登录状态与受保护路由
│   │   ├── components/         # 分页、弹窗、状态等公共组件
│   │   ├── pages/              # 登录、商品和订单页面
│   │   ├── styles/             # 全局样式与设计变量
│   │   └── test/               # 前端页面测试
│   ├── package.json
│   └── vite.config.ts
├── deploy/                     # Compose、前端镜像及 Nginx 配置
└── docs/                       # PRD、设计、架构、计划、运行和测试文档
```

## 如何运行

项目提供了 Docker Compose 配置，可在项目根目录执行：

```bash
docker compose -f deploy/docker-compose.yml up --build
```

停止并移除 Compose 服务：

```bash
docker compose -f deploy/docker-compose.yml down
```

后端测试可执行：

```bash
cd backend
pytest
```

其他环境变量、初始化和运行细节以 `README.md`、`backend/.env.example` 与 `docs/RUNBOOK.md` 为准。

## 验证结果

本次最终质量门结论为：**未通过，不建议按正式上线版本验收**。

- pytest 共执行 **28 项**。
- **25 项通过，3 项失败**。
- 已核对订单精确搜索、分页、详情及待付款订单取消测试结果。
- 已核对商品搜索、状态筛选和分页测试结果。
- 已核对静态体检中的 API 声明、API 实现、前端路由、前端调用、npm 脚本和依赖。
- 静态体检存在 **1 项 frontend high 缺陷**：未识别到 `/products/new` 和 `/products/:id/edit` 对应路由。
- 静态体检结论与前端路由原始事实存在不一致，仍需通过实际浏览器访问重新确认。
- 当前交付状态为 `qa_passed: false`。

## 已知限制

- 后端仍有 3 项 pytest 测试失败，涉及商品或订单查询、分页及订单取消状态历史等主流程，具体失败项需结合测试输出继续定位。
- 商品新建和编辑路由被静态体检判定缺失，尚未形成实际路由访问验证结论。
- `main_image_url` 模型期望 `HttpUrl`，运行时收到 `str`，pytest 输出了 Pydantic 序列化警告。
- Starlette `TestClient` 使用已弃用的 `anyio.abc.BlockingPortal` 别名，后续升级依赖可能出现兼容性问题。
- 当前事实依据未提供前端测试、Playwright 用例及 Docker Compose 启动成功的执行结果。
- 尚未确认全部验收标准在 1280 像素及以上桌面浏览器中的端到端通过情况。
- 支付退款、多规格 SKU、营销、权限体系、复杂库存、物流轨迹、报表和批量操作不在本次范围内。

## 后续可扩展方向

- 修复 3 项 pytest 失败并重新执行完整后端测试。
- 实际访问并确认商品新建、编辑路由，修复路由注册或静态体检规则。
- 执行前端单元测试及 Playwright 管理流程测试。
- 在 1280 像素及以上桌面视口完成登录、商品、订单核心流程的视觉验收。
- 修正 `main_image_url` 类型序列化警告。
- 升级或调整 Starlette、AnyIO 测试依赖，消除弃用风险。
- 验证 Docker Compose 冷启动、健康检查、数据初始化和停止流程。
- 在质量门全部通过后，再形成上线发布包和最终验收确认。
