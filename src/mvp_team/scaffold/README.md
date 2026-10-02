# MVP 项目

> 由「MVP 开发专家团」生成的可运行样机。

## 目录结构

```
.
├── backend/            FastAPI + SQLAlchemy 后端服务
│   ├── app/            应用代码（config / database / models / api / services）
│   ├── tests/          pytest 自动化测试
│   └── requirements.txt
├── frontend/           React + TypeScript + Vite 前端
│   ├── src/            页面、组件、API 封装
│   └── package.json
├── deploy/             部署与启动脚本
│   ├── start.sh        本地一键启动
│   ├── Dockerfile.*    容器镜像
│   └── docker-compose.yml
├── docs/               产品与工程文档
└── Makefile            常用命令入口
```

## 快速开始

```bash
# 一键启动前后端（推荐）
make dev

# 或分别启动
make backend    # http://127.0.0.1:8000/docs
make frontend   # http://127.0.0.1:5173
```

## 运行测试

```bash
make test
```

## 接口文档

后端启动后访问 `/docs` 查看自动生成的 Swagger 文档。

## 环境变量

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `APP_ENV` | 运行环境 | `development` |
| `DATABASE_URL` | 数据库连接串 | `sqlite:///backend/data/app.db` |
| `API_PREFIX` | API 前缀 | `/api` |
| `CORS_ORIGINS` | 允许跨域来源，逗号分隔 | 本地 5173 |

## 容器化部署

```bash
cd deploy && docker compose up --build
# 前端 http://localhost:8080 ｜ 后端 http://localhost:8000
```
