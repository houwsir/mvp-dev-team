from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_admin
from app.api.error_handlers import BusinessError
from app.config import settings
from app.database import get_db
from app.models import AdminUser
from app.schemas.auth import (
    AdminResponse,
    LoginRequest,
    LoginResponse,
)
from app.schemas.common import SuccessResponse
from app.services.auth_service import (
    authenticate,
    create_session,
    revoke_session,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    admin, error = authenticate(db, payload.username, payload.password)
    if error == "ACCOUNT_DISABLED":
        raise BusinessError(403, "管理员账号已禁用", error)
    if admin is None:
        raise BusinessError(401, "账号或密码错误", "INVALID_CREDENTIALS")

    token, session = create_session(db, admin)
    response.set_cookie(
        key="admin_session",
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )
    return LoginResponse(
        admin=AdminResponse.model_validate(admin),
        expires_at=session.expires_at,
    )


@router.post("/logout", response_model=SuccessResponse)
def logout(
    response: Response,
    admin_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    revoke_session(db, admin_session)
    response.delete_cookie(
        "admin_session",
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="strict",
    )
    return SuccessResponse()


@router.get("/me", response_model=AdminResponse)
def me(
    admin: AdminUser = Depends(get_current_admin),
) -> AdminResponse:
    return AdminResponse.model_validate(admin)
