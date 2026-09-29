from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.error_handlers import BusinessError
from app.models import (
    AdminUser,
    OrderShipment,
    OrderStatusHistory,
    ShopOrder,
    utc_now,
)
from app.repositories.order_repository import get_order


def require_order(db: Session, order_id: int) -> ShopOrder:
    order = get_order(db, order_id)
    if order is None:
        raise BusinessError(404, "订单不存在", "ORDER_NOT_FOUND")
    return order


def ship_order(
    db: Session,
    order_id: int,
    logistics_company: str,
    tracking_no: str,
    admin: AdminUser,
) -> ShopOrder:
    if get_order(db, order_id) is None:
        raise BusinessError(404, "订单不存在", "ORDER_NOT_FOUND")

    now = utc_now()
    try:
        result = db.execute(
            update(ShopOrder)
            .where(
                ShopOrder.id == order_id,
                ShopOrder.status == "pending_shipment",
            )
            .values(status="shipped", updated_at=now)
        )
        if result.rowcount != 1:
            db.rollback()
            existing = db.query(OrderShipment).filter_by(
                order_id=order_id
            ).first()
            if existing:
                raise BusinessError(
                    409,
                    "订单已存在物流记录",
                    "SHIPMENT_ALREADY_EXISTS",
                )
            raise BusinessError(
                409,
                "订单当前状态不允许发货",
                "ORDER_STATUS_CONFLICT",
            )

        db.add(
            OrderShipment(
                order_id=order_id,
                logistics_company=logistics_company,
                tracking_no=tracking_no,
                shipped_by=admin.id,
                shipped_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        db.add(
            OrderStatusHistory(
                order_id=order_id,
                from_status="pending_shipment",
                to_status="shipped",
                event_type="shipped",
                operator_type="admin",
                operator_admin_id=admin.id,
                event_note=f"使用{logistics_company}发货",
                created_at=now,
            )
        )
        db.commit()
        db.expire_all()
    except BusinessError:
        raise
    except IntegrityError as exc:
        db.rollback()
        raise BusinessError(
            409,
            "订单已存在物流记录",
            "SHIPMENT_ALREADY_EXISTS",
        ) from exc
    except Exception:
        db.rollback()
        raise

    return require_order(db, order_id)


def cancel_order(
    db: Session,
    order_id: int,
    admin: AdminUser,
) -> ShopOrder:
    current = get_order(db, order_id)
    if current is None:
        raise BusinessError(404, "订单不存在", "ORDER_NOT_FOUND")

    from_status = current.status
    if from_status not in {"pending_payment", "pending_shipment"}:
        raise BusinessError(
            409,
            "订单当前状态不允许取消",
            "ORDER_STATUS_CONFLICT",
        )

    now = utc_now()
    try:
        result = db.execute(
            update(ShopOrder)
            .where(
                ShopOrder.id == order_id,
                ShopOrder.status == from_status,
            )
            .values(status="cancelled", updated_at=now)
        )
        if result.rowcount != 1:
            db.rollback()
            raise BusinessError(
                409,
                "订单已被其他请求处理",
                "ORDER_STATUS_CONFLICT",
            )

        db.add(
            OrderStatusHistory(
                order_id=order_id,
                from_status=from_status,
                to_status="cancelled",
                event_type="cancelled",
                operator_type="admin",
                operator_admin_id=admin.id,
                event_note="管理员取消订单",
                created_at=now,
            )
        )
        db.commit()
        # 关系集合是 selectinload 预加载的，提交后必须让会话失效，
        # 否则随后的读回会命中 identity map，拿到缺少本次新增状态历史的旧对象。
        db.expire_all()
    except BusinessError:
        raise
    except Exception:
        db.rollback()
        raise

    return require_order(db, order_id)


def update_internal_note(
    db: Session,
    order_id: int,
    internal_note: str | None,
) -> ShopOrder:
    order = require_order(db, order_id)
    order.internal_note = internal_note
    order.updated_at = utc_now()
    db.commit()
    db.expire_all()
    return require_order(db, order_id)
