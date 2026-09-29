# 架构说明

## 1. 分层

```
┌─────────────────────────────────────────────────────────────┐
│  CLI 层          cli.py        参数解析、进度渲染、结果汇总     │
├─────────────────────────────────────────────────────────────┤
│  编排层          graph.py      StateGraph 拓扑、条件路由、检查点 │
├─────────────────────────────────────────────────────────────┤
│  角色层          agents/*.py   8 位专家，一人一文件             │
├─────────────────────────────────────────────────────────────┤
│  契约层          prompts.py    角色人设与提示词                │
│                  schemas.py    各角色的结构化输出契约            │
├─────────────────────────────────────────────────────────────┤
│  能力层          llm.py        模型接入 + 结构化输出 + 重试降级   │
│                  tools/        代码块落盘、JSON 抽取、静态体检、  │
│                                子进程执行 pytest / npm build    │
├─────────────────────────────────────────────────────────────┤
│  配置层          config.py     只读环境变量，不绑定厂商          │
└─────────────────────────────────────────────────────────────┘
```

## 2. 共享状态

`TeamState` 是全体专家共写的一块白板，字段按「谁写」来划分：

| 字段 | 写入者 | reducer |
| --- | --- | --- |
| `brief` / `plan` | 项目总监 | 覆盖 |
| `prd` | 产品经理 | 覆盖 |
| `architecture` | 首席架构师 | 覆盖 |
| `design` | UI/UX 设计师 | 覆盖 |
| `backend_files` | 后端工程师 | 覆盖（返工时整体替换） |
| `frontend_files` | 前端工程师 | 覆盖 |
| `test_files` / `test_report` / `qa_passed` / `qa_round` | 测试工程师 | 覆盖 |
| `deploy_files` | 运维工程师 | 覆盖 |
| `docs_files` | 项目总监 / 产品经理 / 架构师 / 设计师 / 测试 / 运维 | **累加** |
| `artifacts` | 全体（全局审计流水） | **累加** |
| `events` | 全体（进度事件） | **累加** |
| `qa_feedback` | 测试工程师（返工依据） | **累加** |
| `run_log` | 全体 | **累加** |

**关键点**：只有在并行分支里会被同时写入的字段才需要累加 reducer。
`backend_files` / `frontend_files` 各只有一个写入者，用覆盖语义反而更合理——
第 2 轮返工时用新产物整体替换旧的，不会让清单里堆满过期文件。

## 3. 一次真实运行的调用序列

```
1.  director_brief     ChatOpenAI(structured=ProjectBrief)
2.  director_plan      ChatOpenAI(structured=DeliveryPlan)     + 落盘 docs/PLAN.md
3.  pm_analyze         ChatOpenAI(structured=PRD)              + 落盘 docs/PRD.md
4.  architect_design ┐ ChatOpenAI(structured=Architecture)     + 落盘 docs/ARCHITECTURE.md
    ui_design        ┘ ChatOpenAI(structured=DesignSpec)       + 落盘 docs/DESIGN.md
                                          ↑ 并行，同一 superstep
5.  backend_dev      ┐ ChatOpenAI(text) → 解析 ```file: 块 → 落盘 backend/**
    frontend_dev     ┘ ChatOpenAI(text) → 解析 ```file: 块 → 落盘 frontend/**
                                          ↑ 并行，都等 4 的两份产出
6.  qa_test            ChatOpenAI(text)  → 写 backend/tests/**
                       subprocess pytest → 原始输出
                       static_checks     → 客观事实
                       ChatOpenAI(structured=TestReport) → 判决
7.  [条件路由]         fail 且未超轮数 → Send 回 5 对应工程师
8.  devops_deploy      ChatOpenAI(text) → 落盘 deploy/**、Makefile、README.md
9.  devops_docs        确定性生成 docs/RUNBOOK.md
10. director_review    ChatOpenAI(text) → docs/HANDOVER.md
```

## 4. 出错与降级策略

| 环节 | 兜底 |
| --- | --- |
| 模型返回非 JSON | `jsonx.extract_json` 四层兜底：裸解析 → 围栏 → 括号配平扫描 → 瑕疵修复 |
| JSON 不合 Schema | 带着校验错误自动重试一次；仍失败则返回 `None`，节点使用确定性兜底值 |
| 模型调用失败 | 指数退避重试 2 次后抛出，CLI 捕获并打印角色名 |
| 模型写越界文件 | `persist_generated(allow=...)` 直接拦截并产生 warn 事件 |
| pytest 跑不起来 | 把「目录不存在 / 无测试文件 / 超时」作为事实写进报告，仍然给出判决 |
| 返工死循环 | `max_qa_rounds` 封顶，超出后带风险交付 |

## 5. 可观测性

每次运行都会留存：

- **CLI 进度流**：每个角色完成即打印一行，带文件名与行数；
- **`events` 列表**：结构化事件，含状态、轮次、数据（如 pytest 原始输出）；
- **`--json` 摘要**：完整运行摘要（项目简报、测试报告、产物清单、事件流），便于接入其他系统；
- **`artifacts` 审计流水**：谁在什么时候写了哪些文件。
