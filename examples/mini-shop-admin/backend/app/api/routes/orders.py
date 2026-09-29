from typing import Literal

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_admin
from app.database import get_db
from app.models import AdminUser, ShopOrder
from app.repositories.order_repository import list_orders
from app.schemas.common import PageSize
from app.schemas.order import (
    CancelOrderRequest,
    InternalNoteRequest,
    OrderDetailResponse,
    OrderItemResponse,
    OrderListItem,
    OrderListResponse,
    ReceiverResponse,
    ShipmentResponse,
    ShipOrderRequest,
    StatusHistoryResponse,
)
from app.services.order_service import (
    cancel_order,
    require_order,
    ship_order,
    update_internal_note,
)


router = APIRouter(
    prefix="/orders",
    tags=["orders"],
    dependencies=[Depends(get_current_admin)],
)


def to_detail(order: ShopOrder) -> OrderDetailResponse:
    shipment = None
    if order.shipment is not None:
        shipment = ShipmentResponse(
            logistics_company=order.shipment.logistics_company,
            tracking_no=order.shipment.tracking_no,
            shipped_by=order.shipment.shipped_by,
            shipped_by_display_name=order.shipment.shipping_admin.display_name,
            shipped_at=order.shipment.shipped_at,
        )

    history = [
        StatusHistoryResponse(
            id=entry.id,
            from_status=entry.from_status,
            to_status=entry.to_status,
            event_type=entry.event_type,
            operator_type=entry.operator_type,
            operator_admin_id=entry.operator_admin_id,
            operator_display_name=(
                entry.operator_admin.display_name
                if entry.operator_admin is not None
                else None
            ),
            event_note=entry.event_note,
            created_at=entry.created_at,
        )
        for entry in order.status_history
    ]

    return OrderDetailResponse(
        id=order.id,
        order_no=order.order_no,
        buyer_id=order.buyer_id,
        buyer_name=order.buyer_name,
        status=order.status,
        items_amount=order.items_amount,
        shipping_fee=order.shipping_fee,
        payable_amount=order.payable_amount,
        receiver=ReceiverResponse(
            name=order.receiver_name,
            phone=order.receiver_phone,
            province=order.receiver_province,
            city=order.receiver_city,
            district=order.receiver_district,
            address=order.receiver_address,
        ),
        buyer_message=order.buyer_message,
        internal_note=order.internal_note,
        placed_at=order.placed_at,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=[
            OrderItemResponse.model_validate(item)
            for item in order.items
        ],
        shipment=shipment,
        status_history=history,
    )


@router.get("", response_model=OrderListResponse)
def orders(
    page: int = Query(default=1, ge=1),
    page_size: PageSize = Query(default=PageSize.DEFAULT),
    order_no: str | None = Query(default=None),
    order_status: Literal[
        "pending_payment",
        "pending_shipment",
        "shipped",
        "completed",
        "cancelled",
    ]
    | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
) -> OrderListResponse:
    items, total = list_orders(
        db,
        page=page,
        page_size=page_size,
        order_no=order_no,
        status=order_status,
    )
    return OrderListResponse(
        items=[OrderListItem.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{order_id}", response_model=OrderDetailResponse)
def detail(
    order_id: int = Path(gt=0),
    db: Session = Depends(get_db),
) -> OrderDetailResponse:
    return to_detail(require_order(db, order_id))


@router.post("/{order_id}/ship", response_model=OrderDetailResponse)
def ship(
    payload: ShipOrderRequest,
    order_id: int = Path(gt=0),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> OrderDetailResponse:
    return to_detail(
        ship_order(
            db,
            order_id,
            payload.logistics_company,
            payload.tracking_no,
            admin,
        )
    )


@router.post("/{order_id}/cancel", response_model=OrderDetailResponse)
def cancel(
    _payload: CancelOrderRequest,
    order_id: int = Path(gt=0),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> OrderDetailResponse:
    return to_detail(cancel_order(db, order_id, admin))


@router.patch(
    "/{order_id}/internal-note",
    response_model=OrderDetailResponse,
)
def internal_note(
    payload: InternalNoteRequest,
    order_id: int = Path(gt=0),
    db: Session = Depends(get_db),
) -> OrderDetailResponse:
    return to_detail(
        update_internal_note(db, order_id, payload.internal_note)
    )
