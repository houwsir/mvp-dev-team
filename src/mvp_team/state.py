"""工作流共享状态定义。

LangGraph 的核心是「共享状态 + 节点函数」。这里的 TeamState 就是 8 位专家
共同读写的那块白板：

* 每个角色只写自己负责的字段；
* 会被**并行节点同时写入**的字段（比如产物清单、事件流）用 ``Annotated[list, add]``
  声明累加型 reducer，LangGraph 会自动把多个分支的结果合并，而不是互相覆盖；
* 只有一个写入者的字段保持默认的「后写覆盖」语义，便于返工时整体替换。
"""

from __future__ import annotations

import operator
from dataclasses import asdict, dataclass, field
from typing import Annotated, Any, TypedDict

# --------------------------------------------------------------------------------------
# 基础数据结构
# --------------------------------------------------------------------------------------


@dataclass
class FileArtifact:
    """一个被真实写入磁盘的产物文件。"""

    path: str
    role: str
    project: str = ""
    bytes: int = 0
    lines: int = 0
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Event:
    """进度事件，用于 CLI 实时输出与审计。"""

    role: str
    title: str
    detail: str = ""
    status: str = "done"          # running | done | warn | fail
    round: int = 1
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------------------
# 状态
# --------------------------------------------------------------------------------------


class TeamState(TypedDict, total=False):
    # ---- 输入 ----
    raw_idea: str                 # 用户原话：「一句话需求」
    project_name: str             # 项目代号（由总监从需求中提炼）
    output_dir: str               # 产物根目录

    # ---- 项目总监 ----
    brief: dict[str, Any]         # 项目简报：目标 / 用户 / 场景 / 范围 / 验收标准
    plan: list[dict[str, Any]]    # 任务拆解与角色分工

    # ---- 产品经理 ----
    prd: dict[str, Any]           # PRD：用户故事 / 功能清单 / 页面 / 数据实体

    # ---- 首席架构师 ----
    architecture: dict[str, Any]  # 技术方案：技术栈 / 数据模型 / API 契约

    # ---- UI/UX 设计师 ----
    design: dict[str, Any]        # 设计规范：信息架构 / 页面布局 / 设计令牌

    # ---- 工程师产物（单写入者，返工时整体替换）----
    backend_files: list[FileArtifact]
    frontend_files: list[FileArtifact]
    test_files: list[FileArtifact]
    deploy_files: list[FileArtifact]

    # ---- 文档类产物（多角色写入，累加合并）----
    docs_files: Annotated[list[FileArtifact], operator.add]

    # ---- 测试与质量门 ----
    test_report: dict[str, Any]
    qa_passed: bool
    qa_round: int
    qa_feedback: Annotated[list[str], operator.add]

    # ---- 全局审计 ----
    artifacts: Annotated[list[FileArtifact], operator.add]
    events: Annotated[list[Event], operator.add]

    # ---- 交付 ----
    summary: str
    run_log: Annotated[list[str], operator.add]


def new_state(idea: str, output_dir: str, project_name: str = "") -> TeamState:
    """构造初始状态。"""
    return TeamState(
        raw_idea=idea,
        project_name=project_name,
        output_dir=output_dir,
        plan=[],
        qa_round=0,
        qa_feedback=[],
        artifacts=[],
        events=[],
        docs_files=[],
        run_log=[],
    )


def event(role: str, title: str, **kwargs: Any) -> dict[str, list[Event]]:
    """便捷构造节点返回值：``{"events": [Event(...)]}``。"""
    return {"events": [Event(role=role, title=title, **kwargs)]}
