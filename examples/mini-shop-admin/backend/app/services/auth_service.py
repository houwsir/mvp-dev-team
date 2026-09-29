from datetime import timedelta
import hashlib
import secrets
import uuid

from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AdminSession, AdminUser, utc_now


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return password_hash.verify(password, encoded)
    except Exception:
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def authenticate(
    db: Session,
    username: str,
    password: str,
) -> tuple[AdminUser | None, str | None]:
    admin = db.scalar(
        select(AdminUser).where(AdminUser.username == username.strip())
    )
    if admin is None or not verify_password(password, admin.password_hash):
        return None, "INVALID_CREDENTIALS"
    if not admin.is_active:
        return None, "ACCOUNT_DISABLED"
    return admin, None


def create_session(
    db: Session,
    admin: AdminUser,
) -> tuple[str, AdminSession]:
    now = utc_now()
    token = secrets.token_urlsafe(48)
    session = AdminSession(
        id=str(uuid.uuid4()),
        admin_user_id=admin.id,
        token_hash=hash_token(token),
        expires_at=now + timedelta(hours=settings.session_ttl_hours),
        created_at=now,
    )
    admin.last_login_at = now
    admin.updated_at = now
    db.add(session)
    db.commit()
    db.refresh(session)
    return token, session


def revoke_session(db: Session, token: str | None) -> None:
    if not token:
        return
    session = db.scalar(
        select(AdminSession).where(
            AdminSession.token_hash == hash_token(token),
            AdminSession.revoked_at.is_(None),
        )
    )
    if session:
        session.revoked_at = utc_now()
        db.commit()
