from datetime import UTC, datetime
from decimal import Decimal
from enum import IntEnum, StrEnum

from pydantic import BaseModel, ConfigDict, field_serializer


class PageSize(IntEnum):
    """分页条数：契约只允许 20 或 50。

    不要写成 `Literal[20, 50]` 直接当 query 参数用 —— query 值永远是字符串，
    FastAPI 不会为 Literal 套 int 转换，会把合法的 `?page_size=20` 判成 422。
    IntEnum 能被正确强转，同时保留「只允许这两个值」的约束。
    """

    DEFAULT = 20
    LARGE = 50


class ProductStatus(StrEnum):
    active = "active"
    inactive = "inactive"


class OrderStatus(StrEnum):
    pending_payment = "pending_payment"
    pending_shipment = "pending_shipment"
    shipped = "shipped"
    completed = "completed"
    cancelled = "cancelled"


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_values(self, value):
        if isinstance(value, Decimal):
            return f"{value:.2f}"
        if isinstance(value, datetime):
            aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value
            return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")
        return value


class ErrorResponse(BaseModel):
    detail: str
    code: str


class SuccessResponse(BaseModel):
    success: bool = True
