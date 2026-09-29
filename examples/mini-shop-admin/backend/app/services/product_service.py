from sqlalchemy.orm import Session

from app.api.error_handlers import BusinessError
from app.models import AdminUser, Product, utc_now
from app.repositories.product_repository import get_product
from app.schemas.product import ProductWrite


def require_product(db: Session, product_id: int) -> Product:
    product = get_product(db, product_id)
    if product is None:
        raise BusinessError(
            404,
            "商品不存在",
            "PRODUCT_NOT_FOUND",
        )
    return product


def create_product(
    db: Session,
    payload: ProductWrite,
    admin: AdminUser,
) -> Product:
    now = utc_now()
    product = Product(
        **payload.model_dump(),
        status="inactive",
        created_by=admin.id,
        updated_by=admin.id,
        created_at=now,
        updated_at=now,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(
    db: Session,
    product_id: int,
    payload: ProductWrite,
    admin: AdminUser,
) -> Product:
    product = require_product(db, product_id)
    for key, value in payload.model_dump().items():
        setattr(product, key, value)
    if product.stock == 0:
        product.status = "inactive"
    product.updated_by = admin.id
    product.updated_at = utc_now()
    db.commit()
    db.refresh(product)
    return product


def update_stock(
    db: Session,
    product_id: int,
    stock: int,
    admin: AdminUser,
) -> Product:
    product = require_product(db, product_id)
    product.stock = stock
    if stock == 0:
        product.status = "inactive"
    product.updated_by = admin.id
    product.updated_at = utc_now()
    db.commit()
    db.refresh(product)
    return product


def update_status(
    db: Session,
    product_id: int,
    status: str,
    admin: AdminUser,
) -> Product:
    product = require_product(db, product_id)
    if status == "active" and product.stock == 0:
        raise BusinessError(
            409,
            "库存为 0，无法上架",
            "PRODUCT_OUT_OF_STOCK",
        )
    product.status = status
    product.updated_by = admin.id
    product.updated_at = utc_now()
    db.commit()
    db.refresh(product)
    return product
