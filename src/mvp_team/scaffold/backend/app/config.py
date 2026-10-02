"""运行时配置。

工程骨架固定了这份「环境变量契约」，业务代码请统一通过 ``get_settings()`` 读取，
不要再去直接读 ``os.environ``，否则测试环境与部署环境会不一致。

| 环境变量 | 含义 | 默认值 |
| --- | --- | --- |
| ``APP_ENV`` | 运行环境（development / test / production） | ``development`` |
| ``DATABASE_URL`` | SQLAlchemy 连接串 | ``sqlite:///backend/data/app.db`` |
| ``API_PREFIX`` | 全局 API 前缀 | ``/api`` |
| ``CORS_ORIGINS`` | 允许的跨域来源，逗号分隔 | 本地 5173 两个地址 |
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = _env(name)
    if not raw:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


class Settings:
    """一次进程运行期间的配置快照。"""

    def __init__(self) -> None:
        self.app_env: str = _env("APP_ENV", "development")
        self.database_url: str = _env(
            "DATABASE_URL", f"sqlite:///{_BACKEND_ROOT / 'data' / 'app.db'}"
        )
        self.api_prefix: str = _env("API_PREFIX", "/api").rstrip("/")
        self.cors_origins: list[str] = _env_list(
            "CORS_ORIGINS",
            ["http://localhost:5173", "http://127.0.0.1:5173"],
        )
        self.is_test: bool = self.app_env.lower() in {"test", "testing"}

    def __repr__(self) -> str:  # pragma: no cover - 仅用于排查
        return (
            f"Settings(app_env={self.app_env!r}, database_url={self.database_url!r}, "
            f"api_prefix={self.api_prefix!r})"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回进程内唯一的配置对象（测试可通过 reload 该模块重置）。"""
    return Settings()


settings = get_settings()
