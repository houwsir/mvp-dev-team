from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class AdminUser(Base):
    __tablename__ = "admin_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class AdminSession(Base):
    __tablename__ = "admin_session"
    __table_args__ = (
        Index("ix_admin_session_admin_user_id", "admin_user_id"),
        Index("ix_admin_session_expires_at", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    admin_user_id: Mapped[int] = mapped_column(
        ForeignKey("admin_user.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )

    admin_user: Mapped[AdminUser] = relationship()


class Product(Base):
    __tablename__ = "product"
    __table_args__ = (
        CheckConstraint("price > 0", name="ck_product_price"),
        CheckConstraint("stock >= 0", name="ck_product_stock"),
        CheckConstraint(
            "status IN ('active','inactive')",
            name="ck_product_status",
        ),
        CheckConstraint(
            "status = 'inactive' OR stock > 0",
            name="ck_product_active_stock",
        ),
        Index("ix_product_name", "name"),
        Index("ix_product_status_updated_at", "status", "updated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    main_image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="inactive",
        server_default="inactive",
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("admin_user.id"),
        nullable=False,
    )
    updated_by: Mapped[int] = mapped_column(
        ForeignKey("admin_user.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class ShopOrder(Base):
    __tablename__ = "shop_order"
    __table_args__ = (
        CheckConstraint(
            "status IN "
            "('pending_payment','pending_shipment','shipped',"
            "'completed','cancelled')",
            name="ck_shop_order_status",
        ),
        CheckConstraint("items_amount >= 0", name="ck_order_items_amount"),
        CheckConstraint("shipping_fee >= 0", name="ck_order_shipping_fee"),
        CheckConstraint("payable_amount >= 0", name="ck_order_payable_amount"),
        CheckConstraint(
            "payable_amount = items_amount + shipping_fee",
            name="ck_shop_order_amount",
        ),
        Index("ix_shop_order_status_placed_at", "status", "placed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
    )
    buyer_id: Mapped[str] = mapped_column(String(64), nullable=False)
    buyer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    items_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    shipping_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payable_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    receiver_name: Mapped[str] = mapped_column(String(100), nullable=False)
    receiver_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    receiver_province: Mapped[str] = mapped_column(String(100), nullable=False)
    receiver_city: Mapped[str] = mapped_column(String(100), nullable=False)
    receiver_district: Mapped[str] = mapped_column(String(100), nullable=False)
    receiver_address: Mapped[str] = mapped_column(String(500), nullable=False)
    buyer_message: Mapped[Optional[str]] = mapped_column(String(500))
    internal_note: Mapped[Optional[str]] = mapped_column(String(1000))
    placed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItem.id",
    )
    shipment: Mapped[Optional["OrderShipment"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        uselist=False,
    )
    status_history: Mapped[list["OrderStatusHistory"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by=lambda: (
            OrderStatusHistory.created_at,
            OrderStatusHistory.id,
        ),
    )


class OrderItem(Base):
    __tablename__ = "order_item"
    __table_args__ = (
        CheckConstraint("unit_price > 0", name="ck_order_item_unit_price"),
        CheckConstraint("quantity > 0", name="ck_order_item_quantity"),
        CheckConstraint("line_amount >= 0", name="ck_order_item_line_amount"),
        Index("ix_order_item_order_id", "order_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("shop_order.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id"),
        nullable=False,
    )
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    product_image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )

    order: Mapped[ShopOrder] = relationship(back_populates="items")


class OrderShipment(Base):
    __tablename__ = "order_shipment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("shop_order.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    logistics_company: Mapped[str] = mapped_column(String(100), nullable=False)
    tracking_no: Mapped[str] = mapped_column(String(100), nullable=False)
    shipped_by: Mapped[int] = mapped_column(
        ForeignKey("admin_user.id"),
        nullable=False,
    )
    shipped_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    order: Mapped[ShopOrder] = relationship(back_populates="shipment")
    shipping_admin: Mapped[AdminUser] = relationship()


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"
    __table_args__ = (
        CheckConstraint(
            "from_status IS NULL OR from_status IN "
            "('pending_payment','pending_shipment','shipped',"
            "'completed','cancelled')",
            name="ck_history_from_status",
        ),
        CheckConstraint(
            "to_status IN "
            "('pending_payment','pending_shipment','shipped',"
            "'completed','cancelled')",
            name="ck_history_to_status",
        ),
        CheckConstraint(
            "event_type IN "
            "('created','payment_confirmed','shipped','completed','cancelled')",
            name="ck_history_event_type",
        ),
        CheckConstraint(
            "operator_type IN ('system','admin')",
            name="ck_history_operator_type",
        ),
        Index(
            "ix_order_status_history_order_time",
            "order_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("shop_order.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[Optional[str]] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    operator_type: Mapped[str] = mapped_column(String(16), nullable=False)
    operator_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("admin_user.id"),
    )
    event_note: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )

    order: Mapped[ShopOrder] = relationship(back_populates="status_history")
    operator_admin: Mapped[Optional[AdminUser]] = relationship()
