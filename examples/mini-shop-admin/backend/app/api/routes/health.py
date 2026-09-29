from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_admin
from app.api.error_handlers import BusinessError
from app.database import get_db
from app.models import Product, ShopOrder


router = APIRouter(tags=["system"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise BusinessError(
            503,
            "服务暂不可用",
            "SERVICE_UNAVAILABLE",
        ) from exc
    return {"status": "ok"}


@router.get(
    "/stats/overview",
    dependencies=[Depends(get_current_admin)],
)
def overview(db: Session = Depends(get_db)) -> dict[str, int]:
    product_total = db.scalar(select(func.count(Product.id))) or 0
    active_products = db.scalar(
        select(func.count(Product.id)).where(Product.status == "active")
    ) or 0
    order_total = db.scalar(select(func.count(ShopOrder.id))) or 0
    pending_shipment = db.scalar(
        select(func.count(ShopOrder.id)).where(
            ShopOrder.status == "pending_shipment"
        )
    ) or 0
    return {
        "product_total": product_total,
        "active_products": active_products,
        "order_total": order_total,
        "pending_shipment_orders": pending_shipment,
    }
