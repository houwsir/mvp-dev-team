"""模型接入层。

**只读环境变量，不绑定任何厂商。** 只要能说 OpenAI 协议就能用：
OpenAI、DeepSeek、通义千问、Moonshot、火山方舟、vLLM、Ollama、one-api……

用法::

    llm = TeamLLM(settings)
    text = llm.say("pm", system=..., user=...)                 # 自由文本
    prd  = llm.structured("pm", system=..., user=..., schema=PRD)  # 结构化
"""

from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from mvp_team.config import Settings
from mvp_team.tools.jsonx import extract_json

T = TypeVar("T", bound=BaseModel)

ROLE_LABELS: dict[str, str] = {
    "director": "项目总监",
    "pm": "产品经理",
    "designer": "UI/UX 设计师",
    "architect": "首席架构师",
    "frontend": "前端工程师",
    "backend": "后端工程师",
    "qa": "测试工程师",
    "devops": "运维工程师",
}


def _flatten_content(content: Any) -> str:
    """把模型返回的 content 统一成纯文本。

    不同网关/模型可能返回：
    * 纯字符串；
    * 内容块数组 ``[{"type": "text", "text": "..."}]``（新版 Responses 风格）；
    * 兼容旧版 ``[{"type": "text", "text": {"value": "..."}}]``。
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
                continue
            if not isinstance(block, dict):
                parts.append(str(block))
                continue
            text = block.get("text", block.get("content", ""))
            if isinstance(text, dict):
                text = text.get("value", "")
            if isinstance(text, list):
                text = _flatten_content(text)
            if text:
                parts.append(str(text))
        return "".join(parts)
    return json.dumps(content, ensure_ascii=False)


class TeamLLM:
    """按角色路由到不同模型（可选），并统一处理结构化输出。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._clients: dict[str, Any] = {}

    # ------------------------------------------------------------------ 客户端
    def _client(self, role: str):
        if self.settings.dry_run:
            return _DryRunClient()
        if role in self._clients:
            return self._clients[role]

        from langchain_openai import ChatOpenAI  # 延迟导入，便于离线环境导入本模块

        kwargs: dict[str, Any] = {
            "model": self.settings.model_for(role),
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
            "timeout": self.settings.request_timeout,
        }
        if self.settings.api_key:
            kwargs["api_key"] = self.settings.api_key
        if self.settings.base_url:
            kwargs["base_url"] = self.settings.base_url

        client = ChatOpenAI(**kwargs)
        self._clients[role] = client
        return client

    # ------------------------------------------------------------------ 调用
    def say(
        self,
        role: str,
        system: str,
        user: str,
        temperature: float | None = None,
        retries: int = 2,
    ) -> str:
        """自由文本调用，带指数退避重试。"""
        client = self._client(role)
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                if temperature is not None and hasattr(client, "temperature"):
                    client = client.model_copy(update={"temperature": temperature})
                message = client.invoke(
                    [
                        ("system", system),
                        ("human", user),
                    ]
                )
                content = getattr(message, "content", message)
                return _flatten_content(content)
            except Exception as exc:  # noqa: BLE001 - 网关错误种类繁多，统一重试
                last_error = exc
                if attempt == retries:
                    break
        raise RuntimeError(f"[{ROLE_LABELS.get(role, role)}] 模型调用失败：{last_error}") from last_error

    def structured(
        self,
        role: str,
        system: str,
        user: str,
        schema: type[T],
        retries: int = 1,
    ) -> T | None:
        """要求模型输出符合 schema 的 JSON，失败自动带错误信息重试一次。"""
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
        contract = (
            "## 输出格式（强制）\n"
            "只输出一个 ```json 代码块，不要有任何额外解释文字。\n"
            "JSON 必须满足以下 JSON Schema：\n"
            f"```json\n{schema_json}\n```"
        )
        prompt = f"{user}\n\n{contract}"

        for attempt in range(retries + 1):
            raw = self.say(role, system=system, user=prompt)
            data = extract_json(raw)
            if data is not None:
                try:
                    return schema.model_validate(data)
                except ValidationError as exc:
                    prompt = (
                        f"{user}\n\n{contract}\n\n"
                        f"上一次输出校验失败：{exc.errors()[:5]}。请严格按 Schema 重新输出，"
                        "确保所有必填字段存在且类型正确。"
                    )
                    continue
            prompt = (
                f"{user}\n\n{contract}\n\n"
                "上一次输出无法解析为 JSON。请只输出 ```json 代码块。"
            )
        return None


# ---------------------------------------------------------------------------------------
# 离线演练客户端
# ---------------------------------------------------------------------------------------


class _DryRunClient:
    """``MVP_DRY_RUN=1`` 时使用：不联网，返回占位内容，用于验证流程拓扑。"""

    def invoke(self, messages: list[tuple[str, str]]):  # noqa: ANN201
        from langchain_core.messages import AIMessage

        user = messages[-1][1] if messages else ""
        return AIMessage(content=_dry_run_reply(user))


def _dry_run_reply(prompt: str) -> str:
    if "JSON Schema" in prompt:
        return "```json\n{}\n```"
    return (
        "# 离线演练产物\n\n"
        "当前处于 dry-run 模式，未调用真实模型。\n\n"
        "```file:DRY_RUN.md\n"
        "# 离线演练占位文件\n\n本文件由 dry-run 模式生成，仅用于验证工作流拓扑。\n"
        "```\n"
    )
