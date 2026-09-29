"""结构化产出模型（Pydantic）。

这些模型既是给模型的「输出契约」，也是运行时的校验器与报告渲染的数据源。
模型不遵守契约时会触发一次自动重试，仍失败则降级为宽松解析。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- 项目总监
class TaskItem(BaseModel):
    id: str = Field(description="任务编号，如 T1")
    title: str
    owner: str = Field(description="负责角色，例如 后端工程师")
    deliverable: str = Field(description="该任务的交付物")
    depends_on: list[str] = Field(default_factory=list)


class ProjectBrief(BaseModel):
    project_name: str = Field(description="英文 kebab-case 项目代号，如 ecom-admin")
    one_liner: str = Field(description="一句话产品定位")
    goal: str = Field(description="核心目标")
    target_users: list[str] = Field(default_factory=list)
    scenarios: list[str] = Field(default_factory=list, description="核心使用场景")
    scope_in: list[str] = Field(default_factory=list, description="本版要做的")
    scope_out: list[str] = Field(default_factory=list, description="本版明确不做的")
    acceptance: list[str] = Field(default_factory=list, description="验收标准")


class DeliveryPlan(BaseModel):
    summary: str = Field(description="方案概述，2-3 句")
    tasks: list[TaskItem] = Field(default_factory=list)


# --------------------------------------------------------------------------- 产品经理
class UserStory(BaseModel):
    id: str
    as_a: str
    i_want: str
    so_that: str
    priority: str = Field(default="P0", description="P0/P1/P2")


class Feature(BaseModel):
    id: str
    name: str
    description: str
    role: str = Field(description="该功能所属角色，如 商品运营")
    priority: str = "P0"


class PageSpec(BaseModel):
    name: str
    route: str
    purpose: str
    key_elements: list[str] = Field(default_factory=list)


class EntityField(BaseModel):
    name: str
    type: str
    required: bool = False
    description: str = ""


class Entity(BaseModel):
    name: str
    description: str = ""
    fields: list[EntityField] = Field(default_factory=list)


class PRD(BaseModel):
    overview: str
    user_stories: list[UserStory] = Field(default_factory=list)
    features: list[Feature] = Field(default_factory=list)
    pages: list[PageSpec] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- 架构师
class ApiEndpoint(BaseModel):
    method: str
    path: str
    summary: str
    request: str = ""
    response: str = ""
    errors: list[str] = Field(default_factory=list)


class DataModel(BaseModel):
    name: str
    table: str
    columns: list[str] = Field(default_factory=list, description="形如 id: INTEGER PK")


class Architecture(BaseModel):
    overview: str
    stack: dict[str, str] = Field(default_factory=dict, description="层次 → 技术选型")
    data_models: list[DataModel] = Field(default_factory=list)
    api_contract: list[ApiEndpoint] = Field(default_factory=list)
    directory_layout: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- 设计师
class DesignToken(BaseModel):
    name: str
    value: str
    usage: str = ""


class PageLayout(BaseModel):
    page: str
    route: str
    layout: str = Field(description="布局描述，如 左侧导航 + 顶部工具栏 + 主内容表格")
    components: list[str] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list, description="空态/加载/错误态")


class DesignSpec(BaseModel):
    style_keywords: list[str] = Field(default_factory=list)
    color_tokens: list[DesignToken] = Field(default_factory=list)
    typography: list[DesignToken] = Field(default_factory=list)
    layouts: list[PageLayout] = Field(default_factory=list)
    interaction_notes: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- 测试
class TestCase(BaseModel):
    id: str
    target: str = Field(description="被测接口或功能")
    steps: list[str] = Field(default_factory=list)
    expected: str


class TestReport(BaseModel):
    verdict: str = Field(description="pass 或 fail")
    summary: str
    executed: list[str] = Field(default_factory=list, description="实际执行的校验项")
    findings: list[dict[str, Any]] = Field(default_factory=list, description="缺陷列表")
    risks: list[str] = Field(default_factory=list)
    rework_for: str = Field(
        default="none",
        description="需要返工的角色，取值 backend / frontend / both / none",
    )


# --------------------------------------------------------------------------- 运维
class DeploySpec(BaseModel):
    overview: str
    artifacts: list[str] = Field(default_factory=list, description="部署产物文件")
    run_steps: list[str] = Field(default_factory=list, description="本地启动步骤")
    env_vars: list[str] = Field(default_factory=list)
    health_checks: list[str] = Field(default_factory=list)
