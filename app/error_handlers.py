"""
全局异常处理器

捕获所有异常并返回统一格式的 JSON 错误响应，同时记录结构化日志。

统一错误响应格式：
{
    "success": false,
    "error": {
        "code": "NOT_FOUND",
        "message": "资源不存在",
        "detail": {}  // 可选的附加信息
    }
}
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.exceptions import AppException
from app.logging_config import logger


def register_exception_handlers(app: FastAPI) -> None:
    """注册所有全局异常处理器"""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """业务异常处理器"""
        logger.warning(
            f"业务异常 [{exc.error_code}] {exc.detail} | path={request.url.path} | "
            f"client={request.client.host if request.client else 'unknown'}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.error_code,
                    "message": exc.detail,
                    "detail": exc.data,
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """请求参数校验异常处理器"""
        errors = exc.errors()
        # 提取第一个错误作为主要信息
        first_error = errors[0] if errors else {}
        loc = " -> ".join(str(l) for l in first_error.get("loc", []))
        msg = first_error.get("msg", "参数校验失败")

        logger.warning(
            f"参数校验失败 | path={request.url.path} | field={loc} | error={msg} | "
            f"client={request.client.host if request.client else 'unknown'}"
        )
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": f"{loc}: {msg}",
                    "detail": errors,
                },
            },
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        """数据库完整性异常处理器（唯一约束冲突等）"""
        error_msg = str(exc.orig) if exc.orig else str(exc)

        # 判断是否为唯一约束冲突
        if "UNIQUE constraint" in error_msg:
            message = "数据重复，请检查唯一字段"
        elif "FOREIGN KEY" in error_msg:
            message = "关联数据不存在或无法删除"
        else:
            message = "数据完整性错误"

        logger.error(
            f"数据库完整性错误 | path={request.url.path} | error={error_msg} | "
            f"client={request.client.host if request.client else 'unknown'}"
        )
        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "error": {
                    "code": "INTEGRITY_ERROR",
                    "message": message,
                    "detail": error_msg,
                },
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
        """数据库异常处理器"""
        logger.exception(
            f"数据库错误 | path={request.url.path} | error={str(exc)} | "
            f"client={request.client.host if request.client else 'unknown'}"
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "数据库操作失败，请稍后重试",
                },
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """兜底异常处理器 - 捕获所有未处理的异常"""
        logger.exception(
            f"未处理异常 | path={request.url.path} | error={str(exc)} | "
            f"client={request.client.host if request.client else 'unknown'}"
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "服务器内部错误，请稍后重试",
                },
            },
        )
