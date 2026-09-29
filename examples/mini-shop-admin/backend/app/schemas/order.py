from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import APIModel, OrderStatus


class OrderListItem(APIModel):
    id: int
    order_no: str
    placed_at: datetime
    buyer_name: str
    payable_amount: Decimal
    status: OrderStatus


class OrderListResponse(APIModel):
    items: list[OrderListItem]
    page: int
    page_size: int
    total: int
    total_pages: int


class ReceiverResponse(BaseModel):
    name: str
    phone: str
    province: str
    city: str
    district: str
    address: str


class OrderItemResponse(APIModel):
    id: int
    product_id: int
    product_name: str
    product_image_url: str
    unit_price: Decimal
    quantity: int
    line_amount: Decimal


class ShipmentResponse(APIModel):
    logistics_company: str
    tracking_no: str
    shipped_by: int
    shipped_by_display_name: str
    shipped_at: datetime


class StatusHistoryResponse(APIModel):
    id: int
    from_status: OrderStatus | None
    to_status: OrderStatus
    event_type: str
    operator_type: str
    operator_admin_id: int | None
    operator_display_name: str | None
    event_note: str | None
    created_at: datetime


class OrderDetailResponse(APIModel):
    id: int
    order_no: str
    buyer_id: str
    buyer_name: str
    status: OrderStatus
    items_amount: Decimal
    shipping_fee: Decimal
    payable_amount: Decimal
    receiver: ReceiverResponse
    buyer_message: str | None
    internal_note: str | None
    placed_at: datetime
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse]
    shipment: ShipmentResponse | None
    status_history: list[StatusHistoryResponse]


class ShipOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    logistics_company: str = Field(max_length=100)
    tracking_no: str = Field(max_length=100)

    @field_validator("logistics_company", "tracking_no")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("不能为空")
        return value


class CancelOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InternalNoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    internal_note: str | None = Field(default=None, max_length=1000)

    @field_validator("internal_note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None
