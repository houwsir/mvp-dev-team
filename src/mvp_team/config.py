"""运行时配置。

设计原则：**只读环境变量，不写死任何端点与密钥**。
所有模型接入信息都从环境变量读取，因此可以无缝切换 OpenAI / DeepSeek / 通义 /
任意 OpenAI 兼容网关（vLLM、Ollama、LiteLLM、one-api 等）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    """极简 .env 加载器：只补齐尚未存在的环境变量，不覆盖已有值。"""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = _env(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _env(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "y", "on"}


@dataclass
class Settings:
    """一次工作流运行的全部可调参数。"""

    # ---- 模型接入（全部来自环境变量）----
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    temperature: float = 0.3
    max_tokens: int = 8192

    # 可以为不同角色指定不同模型（未指定则回落到 model）
    role_models: dict[str, str] = field(default_factory=dict)

    # ---- 工作流行为 ----
    max_qa_rounds: int = 2          # 测试驳回后最多返工轮数
    dry_run: bool = False           # 纯离线演练：不调用真实模型
    install_deps: bool = True       # 质量门前是否按产物 requirements.txt 安装依赖
    verify_frontend: bool = False   # 质量门里是否额外执行 npm install + build（慢，需联网）
    request_timeout: int = 600

    # ---- 产物落盘 ----
    output_dir: Path = field(default_factory=lambda: Path.cwd() / "generated")

    @classmethod
    def load(cls, dotenv: bool = True) -> "Settings":
        if dotenv:
            _load_dotenv(Path.cwd() / ".env")
            _load_dotenv(Path(__file__).resolve().parents[2] / ".env")

        return cls(
            api_key=_env("MVP_API_KEY") or _env("OPENAI_API_KEY"),
            base_url=_env("MVP_BASE_URL") or _env("OPENAI_BASE_URL"),
            model=_env("MVP_MODEL") or _env("OPENAI_MODEL") or "gpt-4o-mini",
            temperature=_env_float("MVP_TEMPERATURE", 0.3),
            max_tokens=_env_int("MVP_MAX_TOKENS", 8192),
            role_models={
                role: value
                for role in (
                    "director", "pm", "designer", "architect",
                    "frontend", "backend", "qa", "devops",
                )
                if (value := _env(f"MVP_MODEL_{role.upper()}"))
            },
            max_qa_rounds=_env_int("MVP_MAX_QA_ROUNDS", 2),
            dry_run=_env_bool("MVP_DRY_RUN", False),
            install_deps=_env_bool("MVP_INSTALL_DEPS", True),
            verify_frontend=_env_bool("MVP_VERIFY_FRONTEND", False),
            request_timeout=_env_int("MVP_REQUEST_TIMEOUT", 600),
        )

    def model_for(self, role: str) -> str:
        return self.role_models.get(role) or self.model or "gpt-4o-mini"

    def validate(self) -> None:
        """真实运行前的配置校验。"""
        if self.dry_run:
            return
        if not self.api_key:
            raise RuntimeError(
                "缺少模型 API Key。请设置环境变量 MVP_API_KEY 或 OPENAI_API_KEY；"
                "若只想离线验证流程，可设置 MVP_DRY_RUN=1。"
            )
