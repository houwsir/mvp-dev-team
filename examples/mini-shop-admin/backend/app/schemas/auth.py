from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import APIModel


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(max_length=64)
    password: str = Field(max_length=128)

    @field_validator("username", "password")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("不能为空")
        return value


class AdminResponse(APIModel):
    id: int
    username: str
    display_name: str


class LoginResponse(APIModel):
    admin: AdminResponse
    expires_at: datetime
