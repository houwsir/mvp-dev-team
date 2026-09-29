from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
)

from app.schemas.common import APIModel, ProductStatus


Price = Annotated[
    Decimal,
    Field(gt=0, le=Decimal("99999999.99"), decimal_places=2),
]


class ProductWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=200)
    main_image_url: HttpUrl
    price: Price
    stock: int = Field(ge=0)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("商品名称不能为空")
        return value

    @field_validator("main_image_url")
    @classmethod
    def normalize_url(cls, value: HttpUrl) -> str:
        url = str(value)
        if len(url) > 2048:
            raise ValueError("主图 URL 最长 2048 个字符")
        return url

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class ProductCreate(ProductWrite):
    pass


class ProductUpdate(ProductWrite):
    pass


class ProductStockUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stock: int = Field(ge=0)


class ProductStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: ProductStatus


class ProductResponse(APIModel):
    id: int
    name: str
    main_image_url: str
    price: Decimal
    stock: int
    description: str | None
    status: ProductStatus
    created_at: datetime
    updated_at: datetime


class ProductListResponse(APIModel):
    items: list[ProductResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
