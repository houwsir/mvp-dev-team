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
✅ 🏛️ 首席架构师·高见远    🧱 工程骨架已铺好
    └ 新建 30｜其中 25 个为受保护骨架文件（工程师不可覆盖）
✅ 🎨 UI/UX 设计师·颜好看   🎨 设计规范已交付
    └ 风格 克制/清晰/高密度 / 色彩令牌 12 个 / 页面布局 4 个
✅ 🏛️ 首席架构师·高见远    🏛️ 技术方案与契约已冻结
    └ 技术选型 5 层 / 数据表 2 张 / 接口 11 个 / 业务文件 18 个
✅ 🖥️ 前端工程师·贾思敏    🖥️ 前端页面已实现
✅ ⚙️ 后端工程师·贝洛奇    ⚙️ 后端服务已实现
✅ 🔍 测试工程师·严过关    🔍 第 1 轮质量门：✅ 放行
    └ 冒烟 通过｜pytest 通过｜契约/静态 high 0 项｜无需返工
✅ 🚀 运维工程师·卜宕机    🚀 部署方案已就绪
✅ 🚀 运维工程师·卜宕机    🧾 交付自检完成
    └ 检查 4 类必备文件，未发现不一致
✅ 🚀 运维工程师·卜宕机    🚦 交付状态已判定
    └ ✅ 通过质量门
✅ 🎬 项目总监·大湾区靓仔   🎉 交付验收完成
```

`cd generated/<项目代号> && make dev` —— 前后端就起来了。

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
| 🚀 运维工程师 | 卜宕机 | 核对部署链路、补运行手册与交付自检 | `deploy/**`、`Makefile`、`README.md`、`RUNBOOK.md`、`DELIVERY_CHECK.md`、`DELIVERY_STATUS.md` |

> 另有一个**不走模型**的节点 `scaffold_baseline`（🧱 工程骨架）：它在架构与设计开工前，
> 用纯代码把构建配置、数据库底座、测试脚手架、部署脚本铺好，并冻结代码级契约。
> 它挂在架构阶段执行，所以不占用独立角色名额。

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
              ┌───────▼─────────┐
              │ scaffold_baseline│  🧱 工程骨架（不走模型）+ 冻结代码级契约
              └───────┬─────────┘
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
              │    qa_test     │  🔍 质量门四道证据：
              └───────┬────────┘     契约一致性 → 静态体检 → 真跑 pytest → 真启动冒烟
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
              │  devops_docs   │  📖 运行手册 + 交付自检 + 交付状态
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
| 轮次上限保护 | `max_qa_rounds` 防止无限返工死循环；额度用尽会标记为「带风险交付」 |
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

# 跳过冒烟门（默认会真启动服务打接口）
mvp-team run "一个电商小程序后台" --no-smoke

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
│   ├── CONTRACT.md              🔒 代码级契约（骨架接口/环境变量/fixture/接口清单）
│   ├── TEST_REPORT_roundN.md    🔍 测试报告（每一轮一份，含冒烟结论）
│   ├── DELIVERY_CHECK.md        🧾 交付一致性自检
│   ├── DELIVERY_STATUS.md       🚦 交付状态（是否通过质量门）
│   ├── RUNBOOK.md               📖 运行手册
│   └── HANDOVER.md              🎉 交付说明
├── backend/                     ⚙️ FastAPI + SQLAlchemy + SQLite
│   ├── app/config.py            🧱 骨架：环境变量契约
│   ├── app/database.py          🧱 骨架：数据访问契约
│   └── tests/conftest.py        🧱 骨架：client / db_session fixture
├── frontend/                    🖥️ React + TypeScript + Vite
├── deploy/                      🧱 Dockerfile / compose / nginx / start.sh
├── Makefile                     🧱 make install / dev / test / build / clean
└── README.md
```

标 🧱 的文件由工程骨架确定性生成，工程师无权覆盖——它们的写入会被拦截并记入事件流。

---

## 4. 为什么它能生成「可运行」的样机

这一节的每一条，都来自**两次真实运行**中被质量门抓到、最终需要人工修复的缺陷复盘。

### 4.1 确定的交给代码，不确定的才交给模型

工程骨架 `scaffold_baseline` 把「不属于业务逻辑的工程基线」用纯代码铺好：
`requirements.txt`、`config.py`、`database.py`、`tests/conftest.py`、`package.json`、
`tsconfig.json`、`vite.config.ts`、`index.html`、`main.tsx`、`Makefile`、
`deploy/start.sh`、两个 Dockerfile、`docker-compose.yml`、`nginx.conf`。

**为什么这条最值钱**：真实运行里反复出现的缺陷全部属于这一类——

| 反复出现的问题 | 根因 |
| --- | --- |
| `Makefile` 引用的 `deploy/start.sh` 不存在 | 部署脚本让模型自由发挥 |
| `docker-compose.yml` 指向不存在的 `Dockerfile.backend` | 同上 |
| `tsconfig.node.json` 配置错误，`npm run build` 直接失败 | 构建配置让模型自由发挥 |
| `vite.config.ts` 混入 vitest 的 `test` 字段，构建报错 | 同上 |
| `conftest.py` 只定义了 1 个 fixture，测试却用了 7 个 | 测试脚手架让模型自由发挥 |

技术栈既然是固定的，这些文件就没有任何创造空间。现在它们由代码生成，
工程师**无权覆盖**（越界写入会被拦截并记入事件流），一次性消灭了这一整类缺陷。
顺带把两位工程师的输出量降了下来——他们只写业务代码。

### 4.2 契约从「HTTP 层」下沉到「代码层」

上一版契约只描述 HTTP 接口，测试与实现之间的**函数级**契约靠各自猜，
结果是 pytest 在收集阶段就中断，两轮返工都没收敛：

| 真实断裂 | 表现 |
| --- | --- |
| 测试 `from app.services.probe_service import probe_http`，实现里只有 `probe_target` | ImportError，一个用例都没跑起来 |
| 测试往 `LATENCY_DATABASE_PATH` 写库，实现读的是 `DATABASE_URL` | 测试环境与实现完全脱节 |
| 测试用了 7 个 fixture，conftest 只定义了 1 个 | 收集阶段中断，全部用例未执行 |

现在骨架把包结构、模块导出、环境变量名、fixture 名**固定下来**，
架构师再产出 `docs/CONTRACT.md` 把它冻结成三方共用的唯一事实来源。
配套的 `tools/contract_check.py` 做**纯确定性**校验：

- 测试导入的符号在实现里是否真的存在（AST 符号表比对）；
- 测试用到的 fixture 是否有定义（已扣除内置 fixture 与 `parametrize` 参数名，零误报）；
- 测试设置的环境变量是否与实现读取的一致；
- 骨架约定的导出符号是否被破坏。

这类问题过去要靠模型审查——既慢又不可靠；现在是静态扫描，稳定复现。

### 4.3 质量门要回答的是「能不能跑起来」

`qa_test` 节点做四件事，全部落在客观证据上：

1. **契约一致性检查**（`contract_check.py`）——符号 / fixture / 环境变量 / 骨架完整性；
2. **静态体检**（`static_checks.py`）——契约声明 vs 实际路由、PRD 页面 vs 前端路由、
   前端调用 vs 后端实现、依赖清单、本地导入；
3. **真跑 pytest**——在子进程里执行，拿原始输出；
4. **冒烟探测**（`smoke.py`）——用独立临时数据库**真启动 uvicorn**，轮询健康检查，
   再按契约把每个无路径参数的 GET 接口打一遍、试打一个 POST。
   带登录的系统会在这一步自动登录（同时支持 `Bearer` token 与 HttpOnly Cookie 会话），
   拿到凭证后再探测受保护接口。

第 4 条是关键补强：真实运行里出现过「59 个 pytest 全绿，但前端 `npm run build` 失败」——
**pytest 全绿不等于产品能跑**。只有真把进程拉起来、真打接口，「可运行」才算有硬证据。

判定有一条硬约束：**只要 pytest 没过、冒烟没过、或存在 high 级缺陷，
verdict 就强制为 `fail`**——模型没有权限「自我感觉良好」。

### 4.4 返工是闭环的，而且信息是够的

上一版的返工提示只给**文件清单**，工程师看不到自己上一轮写了什么，
只能凭记忆重写——这是两轮返工都没收敛的另一个原因。

现在的返工块会把缺陷清单里**被点名文件的当前内容**原样附上，
工程师做定点修复而不是凭空重写。骨架保护的范围也会一并说明，避免它白写一通被拦截。

### 4.5 交付状态不静默

返工额度用尽但质量门仍未放行时，流程会继续走完，但：

- `delivery_status` 标为 `risk`，CLI 用红色明确提示；
- 产出 `docs/DELIVERY_STATUS.md`，写明未通过原因与剩余缺陷；
- 事件流里那一步的状态是 `fail`，不会混在一堆绿色成功事件里；
- CLI 退出码返回 `1`（dry-run 除外）。

**绝不把未通过质量门的产物当成功交付。**

### 4.6 已知陷阱沉淀进提示词

两次真实运行抓到的具体缺陷按角色做成 `KNOWN_PITFALLS` 注入提示词，共 27 条：

- **后端**（8 条）：query 参数不能用 `Literal` 枚举（query 值永远是字符串，FastAPI 不会转，
  带该参数直接 422）；commit 后要 `expire_all()` 否则可能读到变更前的旧值；
  时间统一 UTC + `Z`；并发计数必须用数据库原子操作而不是 `obj.count += 1`……
- **前端**（6 条）：不要动骨架的构建配置；构建命令是 `tsc --noEmit && vite build`，类型错就构建失败……
- **测试**（7 条）：用到自定义 fixture 就必须有定义，否则收集阶段直接中断，一个用例都跑不起来……
- **架构**（3 条）、**运维**（3 条）。

这些不是凭空想出来的防御性条款，每一条都对应一次真实的失败。

### 4.7 产物落盘有协议、有护栏

工程师通过 ```file:相对路径 代码块声明产物，解析器只认带路径的块（普通示例代码块会被忽略），
落盘前还会校验路径不能逃出输出目录。测试工程师越界写 `backend/tests/` 之外的目录、
或任何人试图覆盖骨架文件，都会被拦下并记入事件流。

### 4.8 交付自检补上质量门的盲区

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
│   ├── prompts.py             # 8 位专家人设 + 骨架契约 + 27 条已知陷阱
│   ├── graph.py               # LangGraph 拓扑与运行入口
│   ├── cli.py                 # 命令行
│   ├── scaffold/              # 🧱 工程骨架模板（30 个文件，按产物结构存放）
│   ├── agents/                # 各角色节点实现（一人一文件）
│   │   ├── scaffold_node.py   # 🧱 骨架节点（不走模型）
│   │   └── ...
│   └── tools/
│       ├── codeblocks.py      # ```file: 解析与安全落盘
│       ├── jsonx.py           # 稳健 JSON 抽取（四层兜底）
│       ├── scaffold.py        # 骨架写入 + 骨架所有权清单 + 禁写保护
│       ├── contract_check.py  # 契约一致性（符号/fixture/环境变量/骨架完整性）
│       ├── smoke.py           # 冒烟门：真启动服务、自动登录、打接口
│       ├── static_checks.py   # 确定性静态体检（契约/路由/依赖/导入）
│       ├── delivery_check.py  # 交付一致性自检（Makefile / compose / README）
│       └── runner.py          # 子进程执行 pytest / npm build
├── scripts/verify.py          # 对已有产物做独立复检（不调用模型）
├── tests/                     # 工作流引擎自身的测试（45 项）
└── examples/
    ├── run_demo.sh            # 一键复现示例
    └── mini-shop-admin/       # 真实跑出来的电商后台 MVP（可直接启动）
```

---

## 6. 扩展方式

| 想改什么 | 改哪里 |
| --- | --- |
| 换技术栈（Vue / Next.js / Nest / Go…） | `prompts.py` 里的 `STACK_PROFILE` + 架构师提示词 |
| **调整工程骨架**（依赖版本、构建配置、启动脚本） | 改 `src/mvp_team/scaffold/` 下的模板文件，骨架会自动带上 |
| 加一个角色（比如「安全工程师」） | 在 `agents/` 加一个模块，在 `agents/__init__.py` 的 `build_nodes` 注册，在 `graph.py` 连边 |
| 追加已知陷阱 | `prompts.py` 里的 `KNOWN_PITFALLS`（按角色分组） |
| 换默认模型 / 大小模型混用 | 环境变量 `MVP_MODEL`、`MVP_MODEL_<ROLE>` |
| 调整返工轮数 | `MVP_MAX_QA_ROUNDS` |
| 让质量门连前端构建一起验 | `MVP_VERIFY_FRONTEND=1` |
| 关掉冒烟门 | `MVP_RUN_SMOKE=0` 或 `--no-smoke` |
| 换持久化检查点 | `build_graph(checkpointer=...)` 传入 `SqliteSaver` 等 |

> 骨架模板与产物目录是**同构**的：想给所有产物加一个文件，就在 `scaffold/` 下
> 按相同相对路径放一份即可，无需改代码。

---

## 7. 已知限制

- **产物质量仍取决于模型能力。** 骨架与契约消除了「工程配置类」缺陷，
  但业务逻辑本身写错仍有可能。此时质量门会驳回并触发返工；
  返工轮数用尽仍不通过时会标记为**带风险交付**，并在 `DELIVERY_STATUS.md` 里写明剩余缺陷。
- **编码节点是单次大生成。** 后端/前端各自在一次调用里输出全部业务文件，
  实测完整流水线数十分钟起步，且中途不会有文件落盘（不要用文件数判断是否卡死，看进程）。
  产物接近模型输出上限时存在截断风险，这是后续要做的分片优化方向。
- 当前技术栈基线固定为 FastAPI + SQLite + React/Vite，目的是「生成即可跑」。
- 复杂需求（支付、多租户、权限体系）不在 MVP 范围内，项目总监会主动收敛范围。
- 冒烟门只覆盖**无路径参数**的 GET 接口与一个 POST；带 `{id}` 的接口需要真实数据，
  由 pytest 用例负责。
- 未接入人工审批节点；如需 human-in-the-loop，可在 `qa_test` 之后加 `interrupt`。

---

## 8. 许可

MIT
