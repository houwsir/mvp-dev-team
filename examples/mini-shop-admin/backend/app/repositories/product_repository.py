from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Product


def get_product(db: Session, product_id: int) -> Product | None:
    return db.get(Product, product_id)


def list_products(
    db: Session,
    *,
    page: int,
    page_size: int,
    keyword: str | None,
    status: str | None,
) -> tuple[list[Product], int]:
    filters = []
    normalized_keyword = keyword.strip() if keyword else None
    if normalized_keyword:
        filters.append(Product.name.contains(normalized_keyword))
    if status:
        filters.append(Product.status == status)

    total = db.scalar(
        select(func.count(Product.id)).where(*filters)
    ) or 0
    items = list(
        db.scalars(
            select(Product)
            .where(*filters)
            .order_by(Product.updated_at.desc(), Product.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return items, total
