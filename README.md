# MVP 开发专家团 🎬

> 一句话描述你的想法，8 位专家从调研、设计、编码、测试到部署全流程协作，交付一个**真实可运行**的 MVP 产品源码。

基于 **LangGraph + LangChain** 构建的多智能体工作流。不是「生成一堆看起来像代码的文本」，
而是把代码**真的写进磁盘**、把测试**真的跑起来**、让测试工程师**真的有权驳回**。

```
$ mvp-team run "我想做一个电商小程序后台，用来管理商品和订单"

✅ 🎬 项目总监·大湾区靓仔   📌 锁定项目简报
    └ 面向小型商家的电商小程序后台，用于集中管理商品、库存和订单｜范围 9 项，明确不做 8 项
✅ 🎬 项目总监·大湾区靓仔   🗂️ 完成任务拆解
    └ 7 个任务已指派给团队成员
✅ 📋 产品经理·许清楚      📋 PRD 已定稿
    └ 用户故事 6 条 / 功能 9 项 / 页面 4 个 / 实体 2 个
✅ 🏛️ 首席架构师·高见远    🏛️ 技术方案与契约已冻结
    └ 技术选型 5 层 / 数据表 2 张 / 接口 11 个 / 交付文件 18 个
✅ 🎨 UI/UX 设计师·颜好看   🎨 设计规范已交付
    └ 风格 克制/清晰/高密度 / 色彩令牌 12 个 / 页面布局 4 个
✅ 🖥️ 前端工程师·贾思敏    🖥️ 前端页面已实现
✅ ⚙️ 后端工程师·贝洛奇    ⚙️ 后端服务已实现
✅ 🔍 测试工程师·严过关    🔍 第 1 轮质量门：✅ 放行
    └ pytest 通过｜静态 high 缺陷 0 项
✅ 🚀 运维工程师·卜宕机    🚀 部署方案已就绪
✅ 🎬 项目总监·大湾区靓仔   🎉 交付验收完成
```

---

## 1. 团队与分工

| 角色 | 姓名 | 职责 | 交付物 |
| --- | --- | --- | --- |
| 🎬 项目总监 | 大湾区靓仔 | 一句话 → 项目简报与任务拆解；最终验收 | `PLAN.md`、`HANDOVER.md` |
| 📋 产品经理 | 许清楚 | 需求结构化 | `PRD.md`（用户故事/功能/页面/实体） |
| 🎨 UI/UX 设计师 | 颜好看 | 设计规范 | `DESIGN.md`（色板/字号/布局/交互） |
| 🏛️ 首席架构师 | 高见远 | 技术选型与接口契约 | `ARCHITECTURE.md`（数据模型/API 契约/交付清单） |
| 🖥️ 前端工程师 | 贾思敏 | 前端实现 | `frontend/**` |
| ⚙️ 后端工程师 | 贝洛奇 | 后端实现 | `backend/**` |
| 🔍 测试工程师 | 严过关 | 真实执行的质量门 | `backend/tests/**`、`TEST_REPORT_roundN.md` |
| 🚀 运维工程师 | 卜宕机 | 一键跑起来 | `deploy/**`、`Makefile`、`README.md`、`RUNBOOK.md` |

---

## 2. 工作流拓扑

```
                    START
                      │
              ┌───────▼────────┐
              │ director_brief │  🎬 锁定项目简报 + 项目代号
              └───────┬────────┘
              ┌───────▼────────┐
              │ director_plan  │  🗂️ 任务拆解 + 角色指派
              └───────┬────────┘
              ┌───────▼────────┐
              │   pm_analyze   │  📋 PRD
              └───────┬────────┘
                ╭─────┴─────╮            ← 并行扇出
        ┌───────▼───┐  ┌────▼────────┐
        │ architect │  │  ui_design  │   🏛️ 契约 ／ 🎨 设计
        └───────┬───┘  └────┬────────┘
                ╰─────┬─────╯            ← 菱形汇聚（两位工程师等两份上游）
                ╭─────┴─────╮            ← 并行扇出
        ┌───────▼───┐  ┌────▼────────┐
        │  backend  │  │  frontend   │   ⚙️ 后端 ／ 🖥️ 前端
        └───────┬───┘  └────┬────────┘
                ╰─────┬─────╯            ← 汇流
              ┌───────▼────────┐
              │    qa_test     │  🔍 质量门：真跑 pytest + 静态体检
              └───────┬────────┘
                      │
         ┌────────────┴─────────────┐
         │ 条件路由（可回退）        │
         │ 不通过 → Send 打回工程师  │───┐
         │ 通过   → 继续部署         │   │
         └────────────┬─────────────┘   │
              ┌───────▼────────┐        │
              │ devops_deploy  │  🚀    │
              └───────┬────────┘        │
              ┌───────▼────────┐        │
              │  devops_docs   │  📖    │
              └───────┬────────┘        │
              ┌───────▼────────┐        │
              │ director_review│  🎉    │
              └───────┬────────┘        │
                     END ◄──────────────┘
```

拓扑里用到的 LangGraph 能力：

| 能力 | 在本项目里的体现 |
| --- | --- |
| `StateGraph` + 共享状态 | `TeamState` 就是 8 位专家共用的那块白板 |
| 累加型 reducer | `Annotated[list, operator.add]` 让并行分支的产物清单自动合并而不是互相覆盖 |
| 并行扇出 / 汇聚 | PRD 之后架构与设计同时开工；两位工程师都要等两份上游产出 |
| 条件边 + `Send` | 质量门不通过时把任务**并发送回**对应工程师返工 |
| 轮次上限保护 | `max_qa_rounds` 防止无限返工死循环 |
| 检查点 | 默认 `MemorySaver`，同一个 `thread_id` 可续跑 |
| 流式事件 | `stream_mode="updates"` 驱动 CLI 实时进度 |

---

## 3. 快速开始

### 3.1 安装

```bash
git clone <your-repo-url>
cd mvp-dev-team
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 3.2 配置模型

**代码只读环境变量，不绑定任何厂商。** 任何 OpenAI 兼容端点都能用：
OpenAI、DeepSeek、通义千问、Moonshot、火山方舟、vLLM、Ollama、one-api……

```bash
cp .env.example .env
```

```dotenv
MVP_API_KEY=sk-xxxx
MVP_BASE_URL=https://api.deepseek.com/v1
MVP_MODEL=deepseek-chat
```

也可以直接用标准的 `OPENAI_API_KEY` / `OPENAI_BASE_URL`（优先级低于 `MVP_*`）。

### 3.3 跑起来

```bash
# 一句话生成 MVP
mvp-team run "我想做一个团队任务看板，支持创建任务、拖拽状态、成员分配"

# 产物输出到指定目录
mvp-team run "一个习惯打卡 App" --out ./generated

# 不联网，只验证流程拓扑是否通
mvp-team run "随便什么想法" --dry-run

# 质量门里连前端构建也一起验证（较慢）
mvp-team run "一个电商小程序后台" --verify-frontend

# 查看团队成员 / 工作流拓扑
mvp-team roster
mvp-team graph
```

产物目录结构：

```
generated/<项目代号>/
├── docs/
│   ├── PLAN.md                  🎬 任务拆解
│   ├── PRD.md                   📋 产品需求
│   ├── DESIGN.md                🎨 设计规范
│   ├── ARCHITECTURE.md          🏛️ 技术方案与 API 契约
│   ├── TEST_REPORT_round1.md    🔍 测试报告（每一轮一份）
│   ├── RUNBOOK.md               📖 运行手册
│   └── HANDOVER.md              🎉 交付说明
├── backend/                     ⚙️ FastAPI + SQLAlchemy + SQLite
├── frontend/                    🖥️ React + TypeScript + Vite
├── deploy/                      🚀 Dockerfile / compose / start.sh
├── Makefile
└── README.md
```

---

## 4. 为什么它比「让模型直接写代码」靠谱

### 4.1 契约驱动，前后端不会各写各的

架构师产出的 **API 契约** 是下游两位工程师共用的唯一事实来源。
前端只按契约里的路径和字段写调用，后端只按契约实现路由。

### 4.2 质量门有真实证据，不靠模型自我感觉

`qa_test` 节点做四件事：

1. 让模型写 pytest 用例（**只允许**写 `backend/tests/`，越界写入会被拦下并告警）；
2. 跑确定性静态体检（`tools/static_checks.py`）：契约声明 vs 实际路由、PRD 页面 vs 前端路由、
   前端调用路径 vs 后端实现、依赖清单、本地导入是否指向真实文件；
3. **真的在子进程里执行 `pytest`**，拿原始输出；
4. 把「体检结果 + pytest 输出 + 源码」交给模型出报告。

并且有一条**硬约束**：只要 pytest 没过、或体检存在 high 级缺陷，
就强制把 verdict 改成 `fail`——模型没有权限「自我感觉良好」。

### 4.3 返工是闭环的

判 `fail` 后，缺陷清单原文会被回灌给对应工程师，工程师只重写需要修的文件，
然后重新过质量门。默认最多 2 轮，超出则带风险交付并把结论写进交付说明。

### 4.4 产物落盘有协议、有护栏

工程师通过 ```file:相对路径 代码块声明产物，解析器只认带路径的块（普通示例代码块会被忽略），
落盘前还会校验路径不能逃出输出目录。测试工程师越界写 `backend/` 之外的目录也会被拦下并告警。

### 4.5 交付自检补上质量门的盲区

质量门跑在运维工程师**之前**，所以它验证不了「Makefile 里 `bash deploy/start.sh` 指向的脚本
是否真的存在」这类问题——这正是实际项目里最常见的交付事故。

因此 `devops_docs` 节点会在最后跑一遍**交付一致性自检**（`tools/delivery_check.py`）：

- Makefile 引用的仓库内路径是否存在；
- Makefile 调用的 `npm run <script>` 是否真的在 `package.json` 里定义；
- `docker-compose.yml` 的 dockerfile / context 是否指向真实文件；
- README 里以反引号标注的仓库内路径是否存在；
- 必备交付物是否齐全。

结论写入产物目录的 `docs/DELIVERY_CHECK.md`。

---

## 5. 项目结构

```
mvp-dev-team/
├── src/mvp_team/
│   ├── config.py              # 只读环境变量的运行时配置
│   ├── llm.py                 # 模型接入层 + 结构化输出（带重试与降级）
│   ├── state.py               # TeamState 共享状态与 reducer
│   ├── schemas.py             # 各角色的 Pydantic 输出契约
│   ├── prompts.py             # 8 位专家的人设与提示词
│   ├── graph.py               # LangGraph 拓扑与运行入口
│   ├── cli.py                 # 命令行
│   ├── agents/                # 8 位专家的节点实现（一人一文件）
│   └── tools/
│       ├── codeblocks.py      # ```file: 解析与安全落盘
│       ├── jsonx.py           # 稳健 JSON 抽取（四层兜底）
│       ├── static_checks.py   # 确定性静态体检（契约/路由/依赖/导入）
│       ├── delivery_check.py  # 交付一致性自检（Makefile / compose / README）
│       └── runner.py          # 子进程执行 pytest / npm build
├── scripts/verify.py          # 对已有产物做独立复检（不调用模型）
├── tests/                     # 工作流引擎自身的测试（27 项）
└── examples/
    ├── run_demo.sh            # 一键复现示例
    └── mini-shop-admin/       # 真实跑出来的电商后台 MVP（可直接启动）
```

---

## 6. 扩展方式

| 想改什么 | 改哪里 |
| --- | --- |
| 换技术栈（Vue / Next.js / Nest / Go…） | `prompts.py` 里的 `STACK_PROFILE` + 架构师提示词 |
| 加一个角色（比如「安全工程师」） | 在 `agents/` 加一个模块，在 `agents/__init__.py` 的 `build_nodes` 注册，在 `graph.py` 连边 |
| 换默认模型 / 大小模型混用 | 环境变量 `MVP_MODEL`、`MVP_MODEL_<ROLE>` |
| 调整返工轮数 | `MVP_MAX_QA_ROUNDS` |
| 让质量门连前端构建一起验 | `MVP_VERIFY_FRONTEND=1` |
| 换持久化检查点 | `build_graph(checkpointer=...)` 传入 `SqliteSaver` 等 |

---

## 7. 已知限制

- **产物质量取决于模型能力。** 弱模型可能写出跑不通的代码，此时质量门会驳回并触发返工；
  返工轮数用尽仍不通过时，工作流会带风险交付，并在交付说明里写明。
- 当前技术栈基线固定为 FastAPI + SQLite + React/Vite，目的是「生成即可跑」。
- 复杂需求（支付、多租户、权限体系）不在 MVP 范围内，项目总监会主动收敛范围。
- 未接入人工审批节点；如需 human-in-the-loop，可在 `qa_test` 之后加 `interrupt`。

---

## 8. 许可

MIT
