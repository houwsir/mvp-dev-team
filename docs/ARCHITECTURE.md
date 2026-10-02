# 架构说明

## 1. 分层

```
┌─────────────────────────────────────────────────────────────┐
│  CLI 层          cli.py        参数解析、进度渲染、结果汇总     │
├─────────────────────────────────────────────────────────────┤
│  编排层          graph.py      StateGraph 拓扑、条件路由、检查点 │
├─────────────────────────────────────────────────────────────┤
│  角色层          agents/*.py   8 位专家 + 1 个不走模型的骨架节点 │
├─────────────────────────────────────────────────────────────┤
│  契约层          prompts.py    角色人设、已知陷阱、契约化提示词  │
│                  schemas.py    各角色的结构化输出契约            │
├─────────────────────────────────────────────────────────────┤
│  能力层          llm.py        模型接入 + 结构化输出 + 重试降级   │
│                  tools/        代码块落盘、JSON 抽取、静态体检、  │
│                                工程骨架、契约一致性、冒烟门、     │
│                                子进程执行 pytest / npm build    │
├─────────────────────────────────────────────────────────────┤
│  配置层          config.py     只读环境变量，不绑定厂商          │
└─────────────────────────────────────────────────────────────┘
```

**一条贯穿性原则**：凡是「技术栈固定 ⇒ 没有创造空间」的东西，一律不交给模型，
而是用确定性代码铺好或校验。模型的算力只花在真正需要创造的地方（业务逻辑、界面）。

## 2. 确定性 vs 生成式：三处边界

| 关注点 | 谁负责 | 机制 |
| --- | --- | --- |
| 工程基线（构建配置、测试脚手架、部署脚本、数据库底座） | **代码** | `tools/scaffold.py` 在开工前铺好，工程师禁写（`skeleton_paths()`） |
| 模块导出符号、fixture 名、环境变量名、npm 脚本名 | **代码校验 + 契约文档** | `tools/contract_check.py` AST 扫描；`docs/CONTRACT.md` 交给模型读 |
| 业务逻辑、接口实现、界面结构 | **模型** | 后端 / 前端工程师的提示词 |

- **骨架（skeleton）**：每次运行都被覆盖重写，保证与引擎版本一致。
- **种子（seed）**：只在缺失时写入，允许工程师覆盖；模型漏写时项目仍能构建。
  当前 25 个骨架 + 5 个种子 = 30 个文件。

## 3. 共享状态

`TeamState` 是全体专家共写的一块白板，字段按「谁写」来划分：

| 字段 | 写入者 | reducer |
| --- | --- | --- |
| `brief` / `plan` | 项目总监 | 覆盖 |
| `prd` | 产品经理 | 覆盖 |
| `scaffold_files` | 骨架节点（不走模型） | 覆盖 |
| `architecture` | 首席架构师 | 覆盖 |
| `contract` | 首席架构师（代码级契约） | 覆盖 |
| `design` | UI/UX 设计师 | 覆盖 |
| `backend_files` | 后端工程师 | 覆盖（返工时整体替换） |
| `frontend_files` | 前端工程师 | 覆盖 |
| `test_files` / `test_report` / `qa_passed` / `qa_round` | 测试工程师 | 覆盖 |
| `smoke_report` | 测试工程师（冒烟门原始报告） | 覆盖 |
| `deploy_files` | 运维工程师 | 覆盖 |
| `delivery_status` | 运维工程师 | 覆盖（`pending` → `ok` / `risk`） |
| `docs_files` | 项目总监 / 产品经理 / 架构师 / 设计师 / 测试 / 运维 | **累加** |
| `artifacts` | 全体（全局审计流水） | **累加** |
| `events` | 全体（进度事件） | **累加** |
| `qa_feedback` | 测试工程师（返工依据） | **累加** |
| `run_log` | 全体 | **累加** |

**关键点**：只有在并行分支里会被同时写入的字段才需要累加 reducer。
`backend_files` / `frontend_files` 各只有一个写入者，用覆盖语义反而更合理——
第 2 轮返工时用新产物整体替换旧的，不会让清单里堆满过期文件。

## 4. 一次真实运行的调用序列

```
1.  director_brief     ChatOpenAI(structured=ProjectBrief)
2.  director_plan      ChatOpenAI(structured=DeliveryPlan)     + 落盘 docs/PLAN.md
3.  pm_analyze         ChatOpenAI(structured=PRD)              + 落盘 docs/PRD.md
4.  scaffold_baseline  【不走模型】tools/scaffold.write_scaffold()
                       → 铺 30 个工程基线文件（25 骨架禁写 + 5 种子可覆盖）
5.  architect_design ┐ ChatOpenAI(structured=Architecture)     + 落盘 docs/ARCHITECTURE.md
                       → tools/contract_check.build_contract() + 落盘 docs/CONTRACT.md
    ui_design        ┘ ChatOpenAI(structured=DesignSpec)       + 落盘 docs/DESIGN.md
                                          ↑ 并行，同一 superstep
6.  backend_dev      ┐ ChatOpenAI(text) → 解析 ```file: 块 → 落盘 backend/**
    frontend_dev     ┘ ChatOpenAI(text) → 解析 ```file: 块 → 落盘 frontend/**
                       persist_generated(forbid=skeleton_paths()) 拦截骨架写入
                                          ↑ 并行，都等 5 的两份产出
7.  qa_test            ChatOpenAI(text)  → 写 backend/tests/**（conftest.py 除外）
                       ① contract_check.check_contract()  → 契约一致性（AST，纯确定性）
                       ② static_checks.check_project()    → 静态体检
                       ③ subprocess pytest                → 真跑测试
                       ④ tools/smoke.run_smoke()          → 真启动 uvicorn + 打接口
                       ChatOpenAI(structured=TestReport) → 判决
8.  [条件路由]         fail 且未超轮数 → Send 回 6 对应工程师
                       rework_block 附「被点名文件的当前完整内容」
9.  devops_deploy      ChatOpenAI(text) → 核对/修正 deploy/**、Makefile、README.md
10. devops_docs        确定性生成 docs/RUNBOOK.md
11. director_review    ChatOpenAI(text) → docs/HANDOVER.md
12. [交付判定]         delivery_status = ok / risk → docs/DELIVERY_STATUS.md
                       CLI 退出码：ok → 0，risk → 1
```

## 5. 质量门的四道证据

`qa_test` 节点不是「问模型过没过」，而是**先收齐客观证据，再让模型下判决**：

| 证据 | 手段 | 回答的问题 |
| --- | --- | --- |
| 契约一致性 | AST 扫描（纯确定性） | 测试 import 的符号、用的 fixture、设的环境变量，实现里真的有吗？ |
| 静态体检 | 关键词/结构扫描 | 有没有明显写坏的代码、缺文件、越界写文件？ |
| 单元测试 | 真跑 `pytest` | 逻辑对不对？ |
| 冒烟门 | 真启动服务 + 打接口 | **这个产物到底能不能跑起来？** |

**冒烟门（smoke gate）细节**：

- 用独立临时 SQLite（`DATABASE_URL=sqlite:///<tmp>/smoke.db`），不污染产物数据；
- `subprocess.Popen` 启动 `uvicorn`，轮询健康检查（`/api/health`、`/health` 等候选）；
- 从接口契约里找登录接口，自动登录，**同时支持 `Bearer` token 与 HttpOnly Cookie** 两种会话
  （用 `http.cookiejar.CookieJar()` 贯穿整轮请求）；
- 按契约挑安全的 GET / POST 探针（跳过带 `{id}` 的路径与登录接口）；
- 任一探针返回 5xx 或连接失败 → 冒烟失败；401/403/405 视为「接口存在但需要鉴权」，不算失败。

## 6. 出错与降级策略

| 环节 | 兜底 |
| --- | --- |
| 模型返回非 JSON | `jsonx.extract_json` 四层兜底：裸解析 → 围栏 → 括号配平扫描 → 瑕疵修复 |
| JSON 不合 Schema | 带着校验错误自动重试一次；仍失败则返回 `None`，节点使用确定性兜底值 |
| 模型调用失败 | 指数退避重试 2 次后抛出，CLI 捕获并打印角色名 |
| 模型写越界文件 | `persist_generated(allow=...)` 直接拦截并产生 warn 事件 |
| 模型想覆盖工程骨架 | `persist_generated(forbid=skeleton_paths())` 拦截 + `🛡️ 骨架文件保护拦截` 事件 |
| 骨架模板缺失 | `ensure_template_root()` 立刻抛错，不静默继续 |
| pytest 跑不起来 | 把「目录不存在 / 无测试文件 / 超时」作为事实写进报告，仍然给出判决 |
| 冒烟起不来 | 记录启动日志与超时事实，判定 `smoke_ok=False`，进入返工 |
| 返工死循环 | `max_qa_rounds` 封顶；额度用尽 → **不静默降级**，`delivery_status="risk"` |

## 7. 交付状态：不静默降级

返工额度用尽但质量门仍未通过时，**绝不把未过门的产物当成功交付**：

- `delivery_status = "risk"` 写进状态；
- 落盘 `docs/DELIVERY_STATUS.md`，写明未通过的检查项与残余缺陷；
- CLI 打印 `⚠️ 带风险交付` 并以**退出码 1** 结束；
- `--json` 摘要里同时给出 `delivery_status` / `smoke_passed` / `contract`。

只有 `delivery_status == "ok"` 才代表「产物通过了全部质量门」。

## 8. 可观测性

每次运行都会留存：

- **CLI 进度流**：每个角色完成即打印一行，带文件名与行数；
- **`events` 列表**：结构化事件，含状态、轮次、数据（如 pytest / 冒烟原始输出）；
- **`--json` 摘要**：完整运行摘要（项目简报、测试报告、契约结论、交付状态、产物清单、事件流）；
- **`artifacts` 审计流水**：谁在什么时候写了哪些文件。
