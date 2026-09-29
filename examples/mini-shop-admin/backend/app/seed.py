from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    AdminUser,
    OrderItem,
    OrderShipment,
    OrderStatusHistory,
    Product,
    ShopOrder,
    utc_now,
)
from app.services.auth_service import hash_password


PRODUCTS = [
    ("云南高山蓝莓 125g", "39.90", 86, "active", "当季鲜果，冷链配送"),
    ("原切谷饲牛排 200g", "68.00", 42, "active", "谷饲原切，单片独立包装"),
    ("有机纯牛奶 250ml×12", "59.90", 120, "active", "常温全脂纯牛奶"),
    ("冷萃黑咖啡液 12颗", "49.00", 64, "active", "零蔗糖浓缩咖啡液"),
    ("新疆灰枣 500g", "32.80", 0, "inactive", "肉厚核小，开袋即食"),
    ("山茶花洗衣液 2kg", "45.90", 35, "active", "低泡易漂洗，清新花香"),
    ("便携保温杯 480ml", "79.00", 18, "inactive", "食品级不锈钢内胆"),
    ("抽取式厨房纸 3包", "25.90", 97, "active", "吸油吸水，可接触食品"),
]


ORDER_SEEDS = [
    ("202506180001", "林晓雯", "pending_payment", 0, None),
    ("202506180002", "陈宇航", "pending_shipment", 1, "工作日发货"),
    ("202506170003", "周静", "pending_shipment", 2, None),
    ("202506160004", "王海峰", "shipped", 3, "放在门卫室"),
    ("202506150005", "赵敏", "completed", 5, None),
    ("202506140006", "刘晨", "cancelled", 6, "地址填写错误"),
]


def seed_database(db: Session) -> None:
    admin = db.scalar(
        select(AdminUser).where(
            AdminUser.username == settings.seed_admin_username
        )
    )
    now = utc_now()
    if admin is None:
        admin = AdminUser(
            username=settings.seed_admin_username,
            password_hash=hash_password(settings.seed_admin_password),
            display_name="商城管理员",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(admin)
        db.flush()

    if (db.scalar(select(func.count(Product.id))) or 0) == 0:
        for index, (name, price, stock, status, description) in enumerate(
            PRODUCTS,
            start=1,
        ):
            db.add(
                Product(
                    name=name,
                    main_image_url=(
                        f"https://images.unsplash.com/photo-"
                        f"1542838132-92c53300491e?seed={index}"
                    ),
                    price=Decimal(price),
                    stock=stock,
                    description=description,
                    status=status,
                    created_by=admin.id,
                    updated_by=admin.id,
                    created_at=now - timedelta(days=10 - index),
                    updated_at=now - timedelta(days=8 - index),
                )
            )
        db.flush()

    if (db.scalar(select(func.count(ShopOrder.id))) or 0) == 0:
        products = list(db.scalars(select(Product).order_by(Product.id)))
        for index, (
            order_no,
            buyer_name,
            status,
            product_index,
            message,
        ) in enumerate(ORDER_SEEDS):
            product = products[product_index]
            quantity = 2 if index == 2 else 1
            items_amount = product.price * quantity
            shipping_fee = Decimal("0.00") if items_amount >= 59 else Decimal("8.00")
            placed_at = now - timedelta(days=index, hours=index + 1)

            order = ShopOrder(
                order_no=order_no,
                buyer_id=f"buyer-{1001 + index}",
                buyer_name=buyer_name,
                status=status,
                items_amount=items_amount,
                shipping_fee=shipping_fee,
                payable_amount=items_amount + shipping_fee,
                receiver_name=buyer_name,
                receiver_phone=f"1380000000{index}",
                receiver_province="广东省",
                receiver_city="深圳市",
                receiver_district="南山区",
                receiver_address=f"科技南路 {18 + index} 号 {index + 1} 栋",
                buyer_message=message,
                internal_note="高价值客户，优先处理" if index == 1 else None,
                placed_at=placed_at,
                created_at=placed_at,
                updated_at=placed_at,
            )
            db.add(order)
            db.flush()
            db.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    product_name=product.name,
                    product_image_url=product.main_image_url,
                    unit_price=product.price,
                    quantity=quantity,
                    line_amount=items_amount,
                    created_at=placed_at,
                )
            )

            initial_status = (
                "pending_payment"
                if status in {"pending_payment", "cancelled"}
                else "pending_shipment"
            )
            db.add(
                OrderStatusHistory(
                    order_id=order.id,
                    from_status=None,
                    to_status=initial_status,
                    event_type="created",
                    operator_type="system",
                    created_at=placed_at,
                )
            )

            if status == "shipped":
                shipped_at = placed_at + timedelta(hours=4)
                db.add(
                    OrderShipment(
                        order_id=order.id,
                        logistics_company="顺丰速运",
                        tracking_no=f"SF202506{index:06d}",
                        shipped_by=admin.id,
                        shipped_at=shipped_at,
                        created_at=shipped_at,
                        updated_at=shipped_at,
                    )
                )
                db.add(
                    OrderStatusHistory(
                        order_id=order.id,
                        from_status="pending_shipment",
                        to_status="shipped",
                        event_type="shipped",
                        operator_type="admin",
                        operator_admin_id=admin.id,
                        event_note="顺丰速运发货",
                        created_at=shipped_at,
                    )
                )
            elif status == "completed":
                shipped_at = placed_at + timedelta(hours=3)
                completed_at = placed_at + timedelta(days=2)
                db.add(
                    OrderShipment(
                        order_id=order.id,
                        logistics_company="京东物流",
                        tracking_no=f"JD202506{index:06d}",
                        shipped_by=admin.id,
                        shipped_at=shipped_at,
                        created_at=shipped_at,
                        updated_at=shipped_at,
                    )
                )
                db.add_all(
                    [
                        OrderStatusHistory(
                            order_id=order.id,
                            from_status="pending_shipment",
                            to_status="shipped",
                            event_type="shipped",
                            operator_type="admin",
                            operator_admin_id=admin.id,
                            event_note="京东物流发货",
                            created_at=shipped_at,
                        ),
                        OrderStatusHistory(
                            order_id=order.id,
                            from_status="shipped",
                            to_status="completed",
                            event_type="completed",
                            operator_type="system",
                            event_note="订单已完成",
                            created_at=completed_at,
                        ),
                    ]
                )
            elif status == "cancelled":
                db.add(
                    OrderStatusHistory(
                        order_id=order.id,
                        from_status="pending_payment",
                        to_status="cancelled",
                        event_type="cancelled",
                        operator_type="admin",
                        operator_admin_id=admin.id,
                        event_note="管理员取消订单",
                        created_at=placed_at + timedelta(minutes=30),
                    )
                )

    db.commit()
