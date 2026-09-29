from typing import Literal

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_admin
from app.database import get_db
from app.models import AdminUser
from app.repositories.product_repository import list_products
from app.schemas.common import PageSize
from app.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductStatusUpdate,
    ProductStockUpdate,
    ProductUpdate,
)
from app.services.product_service import (
    create_product,
    require_product,
    update_product,
    update_status,
    update_stock,
)


router = APIRouter(
    prefix="/products",
    tags=["products"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("", response_model=ProductListResponse)
def products(
    page: int = Query(default=1, ge=1),
    page_size: PageSize = Query(default=PageSize.DEFAULT),
    keyword: str | None = Query(default=None),
    product_status: Literal["active", "inactive"] | None = Query(
        default=None,
        alias="status",
    ),
    db: Session = Depends(get_db),
) -> ProductListResponse:
    items, total = list_products(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        status=product_status,
    )
    return ProductListResponse(
        items=[ProductResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> ProductResponse:
    return ProductResponse.model_validate(
        create_product(db, payload, admin)
    )


@router.get("/{product_id}", response_model=ProductResponse)
def detail(
    product_id: int = Path(gt=0),
    db: Session = Depends(get_db),
) -> ProductResponse:
    return ProductResponse.model_validate(
        require_product(db, product_id)
    )


@router.put("/{product_id}", response_model=ProductResponse)
def update(
    payload: ProductUpdate,
    product_id: int = Path(gt=0),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> ProductResponse:
    return ProductResponse.model_validate(
        update_product(db, product_id, payload, admin)
    )


@router.patch("/{product_id}/stock", response_model=ProductResponse)
def stock(
    payload: ProductStockUpdate,
    product_id: int = Path(gt=0),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> ProductResponse:
    return ProductResponse.model_validate(
        update_stock(db, product_id, payload.stock, admin)
    )


@router.patch("/{product_id}/status", response_model=ProductResponse)
def change_status(
    payload: ProductStatusUpdate,
    product_id: int = Path(gt=0),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> ProductResponse:
    return ProductResponse.model_validate(
        update_status(db, product_id, payload.status.value, admin)
    )
