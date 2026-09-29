from fastapi import Cookie, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.error_handlers import BusinessError
from app.database import get_db
from app.models import AdminSession, AdminUser, utc_now
from app.services.auth_service import hash_token


def get_current_admin(
    admin_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> AdminUser:
    if not admin_session:
        raise BusinessError(401, "请先登录", "AUTH_REQUIRED")

    session = db.scalar(
        select(AdminSession).where(
            AdminSession.token_hash == hash_token(admin_session)
        )
    )
    if session is None:
        raise BusinessError(401, "请先登录", "AUTH_REQUIRED")

    if session.revoked_at is not None or session.expires_at <= utc_now():
        raise BusinessError(401, "登录会话已失效", "SESSION_EXPIRED")

    admin = db.get(AdminUser, session.admin_user_id)
    if admin is None:
        raise BusinessError(401, "请先登录", "AUTH_REQUIRED")
    if not admin.is_active:
        raise BusinessError(403, "管理员账号已禁用", "ACCOUNT_DISABLED")
    return admin
