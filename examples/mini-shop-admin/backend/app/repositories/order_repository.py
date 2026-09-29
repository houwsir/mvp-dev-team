from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    OrderShipment,
    OrderStatusHistory,
    ShopOrder,
)


def list_orders(
    db: Session,
    *,
    page: int,
    page_size: int,
    order_no: str | None,
    status: str | None,
) -> tuple[list[ShopOrder], int]:
    filters = []
    normalized_order_no = order_no.strip() if order_no else None
    if normalized_order_no:
        filters.append(ShopOrder.order_no == normalized_order_no)
    if status:
        filters.append(ShopOrder.status == status)

    total = db.scalar(
        select(func.count(ShopOrder.id)).where(*filters)
    ) or 0
    items = list(
        db.scalars(
            select(ShopOrder)
            .where(*filters)
            .order_by(ShopOrder.placed_at.desc(), ShopOrder.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return items, total


def get_order(db: Session, order_id: int) -> ShopOrder | None:
    statement = (
        select(ShopOrder)
        .where(ShopOrder.id == order_id)
        .options(
            selectinload(ShopOrder.items),
            selectinload(ShopOrder.shipment).selectinload(
                OrderShipment.shipping_admin
            ),
            selectinload(ShopOrder.status_history).selectinload(
                OrderStatusHistory.operator_admin
            ),
        )
    )
    return db.scalar(statement)
