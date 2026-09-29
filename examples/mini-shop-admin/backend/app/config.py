from dataclasses import dataclass
import os


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str
    session_ttl_hours: int
    session_cookie_secure: bool
    seed_admin_username: str
    seed_admin_password: str
    cors_origin: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.getenv(
                "DATABASE_URL",
                "sqlite:///./mini-shop-admin.db",
            ),
            session_ttl_hours=int(os.getenv("SESSION_TTL_HOURS", "8")),
            session_cookie_secure=parse_bool(
                os.getenv("SESSION_COOKIE_SECURE", "false")
            ),
            seed_admin_username=os.getenv("SEED_ADMIN_USERNAME", "admin").strip(),
            seed_admin_password=os.getenv(
                "SEED_ADMIN_PASSWORD",
                "admin123456",
            ),
            cors_origin=os.getenv(
                "CORS_ORIGIN",
                "http://localhost:5173",
            ),
        )


settings = Settings.from_env()
