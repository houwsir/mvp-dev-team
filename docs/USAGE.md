# 使用说明（小白也能看懂版）

## 0. 这套东西到底在干嘛？

打个比方。

平时你想做个产品，得找人：一个想清楚要做什么的产品经理、一个设计界面的设计师、
一个定技术方案的架构师、两个写代码的工程师、一个挑毛病的测试、一个负责把它跑起来的运维。
找齐这些人要花很多钱和时间。

**MVP 开发专家团**就是把这 8 个人「装进一个程序里」：

> 你只说一句「我想做一个电商小程序后台」，
> 程序就会按顺序叫这 8 个 AI 角色干活，最后在磁盘上生成一个**真的能跑起来的小网站**。

它跟「让 AI 直接写代码」最大的区别是：

- 每个角色**只干自己那份活**，干完把成果交给下一个人；
- 前后端都按**同一份接口契约**写，不会各写各的；
- 测试工程师会**真的把测试跑起来**，跑不过就把活退回去重做。

---

## 1. 五分钟跑通

### 第一步：装环境

```bash
cd mvp-dev-team
python -m venv .venv
source .venv/bin/activate          # Windows 用 .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### 第二步：告诉它用哪个 AI 模型

程序**不绑定任何厂商**，只要对方支持 OpenAI 协议就行
（OpenAI、DeepSeek、通义千问、Moonshot、火山方舟，或者你自己搭的 vLLM/Ollama 都行）。

```bash
cp .env.example .env
```

打开 `.env`，填三行：

```dotenv
MVP_API_KEY=你的密钥
MVP_BASE_URL=https://api.deepseek.com/v1     # 换成你用的服务地址
MVP_MODEL=deepseek-chat                       # 换成你要用的模型名
```

> 不确定填什么？去看你用的模型服务商的文档，找「base_url」和「model」这两项。

### 第三步：跑

```bash
mvp-team run "我想做一个电商小程序后台，用来管理商品和订单"
```

然后你会看到八个角色挨个汇报进度，最后在 `generated/` 目录下看到成果。

---

## 2. 你会得到什么

```
generated/mini-shop-admin/
├── docs/
│   ├── PLAN.md              项目总监的任务拆解
│   ├── PRD.md               产品经理的需求文档
│   ├── DESIGN.md            设计师的界面规范
│   ├── ARCHITECTURE.md      架构师的技术方案 + 接口清单
│   ├── TEST_REPORT_round1.md 测试报告
│   ├── RUNBOOK.md           怎么把项目跑起来
│   └── HANDOVER.md          交付说明
├── backend/                 后端代码（Python / FastAPI）
├── frontend/                前端代码（React / TypeScript）
├── deploy/                  部署脚本、Docker 配置
├── Makefile
└── README.md
```

### 怎么把生成的产品跑起来

```bash
# 方式一：一键启动
cd generated/mini-shop-admin
bash deploy/start.sh

# 方式二：分开启动
# 后端 → http://localhost:8000
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端 → http://localhost:5173
cd frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:5173` 就能看到界面了。

---

## 3. 八个角色分别在干什么

| 顺序 | 角色 | 通俗解释 | 产出 |
| --- | --- | --- | --- |
| 1 | 🎬 项目总监 | 把你说的一句话，翻译成「要做什么、不做什么」 | `PLAN.md` |
| 2 | 📋 产品经理 | 想清楚有哪些页面、哪些功能、数据长什么样 | `PRD.md` |
| 3 | 🏛️ 首席架构师 | 定技术方案，并把接口一个字段一个字段地写清楚 | `ARCHITECTURE.md` |
| 4 | 🎨 UI/UX 设计师 | 定颜色、字号、每个页面怎么排版 | `DESIGN.md` |
| 5 | ⚙️ 后端工程师 | 写服务器代码，把接口真的实现出来 | `backend/**` |
| 6 | 🖥️ 前端工程师 | 写页面代码，调用后端接口把界面做出来 | `frontend/**` |
| 7 | 🔍 测试工程师 | **真的跑测试**，有问题就打回去重做 | `backend/tests/**`、测试报告 |
| 8 | 🚀 运维工程师 | 写一键启动脚本、Docker 配置 | `deploy/**`、`RUNBOOK.md` |

> 第 3、4 步是**同时**进行的，第 5、6 步也是。这就是「并行」，能省一半时间。

---

## 4. 常见问题

### Q1：`mvp-team: command not found`

没执行 `pip install -e .`。或者直接用模块方式运行：

```bash
PYTHONPATH=src python -m mvp_team run "你的需求"
```

### Q2：报错「缺少模型 API Key」

`.env` 里的 `MVP_API_KEY` 没填，或者环境变量没生效。可以先用离线模式确认流程本身没问题：

```bash
mvp-team run "随便什么想法" --dry-run
```

`--dry-run` 不会联网，只验证「八个角色能不能按顺序串起来」。

### Q3：质量门一直不通过怎么办？

默认最多返工 2 轮，超过就会带着风险继续交付，并在 `HANDOVER.md` 里写明问题。
想看更严格的把关（连前端构建也一起验证）：

```bash
mvp-team run "你的需求" --verify-frontend
```

想让它多返工几轮：

```bash
mvp-team run "你的需求" --max-qa-rounds 3
```

如果反复失败，多半是模型能力不够。换一个更强的模型（改 `MVP_MODEL`）通常最有效。

### Q4：我不想用 FastAPI + React，想换成 Vue / Next.js / Go

改 `src/mvp_team/prompts.py` 里的 `STACK_PROFILE`，以及架构师那段提示词里的技术栈描述。
两个工程师是照着架构师的契约写代码的，契约变了，产物就会跟着变。

### Q5：想加一个「安全工程师」角色

三步：

1. 在 `src/mvp_team/agents/` 下新建一个文件，写一个 `make_nodes(llm, settings)` 函数；
2. 在 `src/mvp_team/agents/__init__.py` 的 `build_nodes` 里注册它；
3. 在 `src/mvp_team/graph.py` 里给它连上前后节点。

### Q6：产物目录能改吗

可以：

```bash
mvp-team run "你的需求" --out ~/Desktop/my-project
```

### Q7：怎么知道每个角色花了多久、写了哪些文件

```bash
mvp-team run "你的需求" --json
```

会在结尾额外打印一份 JSON 摘要，包含所有事件流和产物清单。

---

## 5. 命令速查

| 命令 | 作用 |
| --- | --- |
| `mvp-team run "<需求>"` | 跑完整流水线 |
| `mvp-team run "<需求>" --out <目录>` | 指定产物目录 |
| `mvp-team run "<需求>" --dry-run` | 不联网，只验证流程 |
| `mvp-team run "<需求>" --verify-frontend` | 质量门里额外做前端构建 |
| `mvp-team run "<需求>" --max-qa-rounds N` | 设置最多返工轮数 |
| `mvp-team run "<需求>" --json` | 额外输出 JSON 摘要 |
| `mvp-team roster` | 查看团队成员 |
| `mvp-team graph` | 查看工作流拓扑 |

常用环境变量：

| 变量 | 作用 | 默认 |
| --- | --- | --- |
| `MVP_API_KEY` | 模型密钥 | 无（必填） |
| `MVP_BASE_URL` | 模型服务地址 | 无（走官方默认） |
| `MVP_MODEL` | 模型名 | `gpt-4o-mini` |
| `MVP_MODEL_<角色>` | 给单个角色单独指定模型 | 无 |
| `MVP_MAX_QA_ROUNDS` | 最多返工轮数 | `2` |
| `MVP_INSTALL_DEPS` | 质量门前是否安装产物依赖 | `1` |
| `MVP_VERIFY_FRONTEND` | 质量门是否验证前端构建 | `0` |
| `MVP_DRY_RUN` | 离线演练 | `0` |
| `MVP_TEMPERATURE` | 采样温度 | `0.3` |
| `MVP_MAX_TOKENS` | 单次输出上限 | `8192` |

> 小技巧：模型名越强，产物越靠谱。如果发现生成的代码经常跑不通，
> 把 `MVP_MODEL` 换成更强的型号，或者用 `MVP_MODEL_ARCHITECT`、`MVP_MODEL_BACKEND`
> 只给关键角色上强模型，其他角色用便宜的，可以省钱。
