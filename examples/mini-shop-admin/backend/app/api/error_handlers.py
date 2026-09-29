import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


logger = logging.getLogger(__name__)


class BusinessError(Exception):
    def __init__(self, status_code: int, detail: str, code: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.code = code


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def handle_business_error(
        _request: Request,
        exc: BusinessError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request,
        _exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": "请求参数不符合要求",
                "code": "VALIDATION_ERROR",
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        _request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        detail = str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": detail, "code": code},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception(
            "Unhandled error for %s %s",
            request.method,
            request.url.path,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "服务器内部错误",
                "code": "INTERNAL_SERVER_ERROR",
            },
        )
