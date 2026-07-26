"""
自定义异常类

提供统一的业务异常基类，所有业务层抛出的异常都应使用这些类。
全局异常处理器会捕获这些异常并返回统一格式的错误响应。
"""
from typing import Any, Optional


class AppException(Exception):
    """应用基础异常类"""

    def __init__(
        self,
        status_code: int = 500,
        detail: str = "服务器内部错误",
        error_code: Optional[str] = None,
        data: Optional[Any] = None,
    ):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code or f"ERR_{status_code}"
        self.data = data
        super().__init__(detail)


class NotFoundException(AppException):
    """资源不存在"""

    def __init__(self, detail: str = "资源不存在", error_code: str = "NOT_FOUND"):
        super().__init__(status_code=404, detail=detail, error_code=error_code)


class BadRequestException(AppException):
    """请求参数错误"""

    def __init__(self, detail: str = "请求参数错误", error_code: str = "BAD_REQUEST"):
        super().__init__(status_code=400, detail=detail, error_code=error_code)


class UnauthorizedException(AppException):
    """未认证"""

    def __init__(self, detail: str = "未认证，请先登录", error_code: str = "UNAUTHORIZED"):
        super().__init__(status_code=401, detail=detail, error_code=error_code)


class ForbiddenException(AppException):
    """无权限"""

    def __init__(self, detail: str = "无权限执行此操作", error_code: str = "FORBIDDEN"):
        super().__init__(status_code=403, detail=detail, error_code=error_code)


class ConflictException(AppException):
    """资源冲突"""

    def __init__(self, detail: str = "资源冲突", error_code: str = "CONFLICT"):
        super().__init__(status_code=409, detail=detail, error_code=error_code)


class RateLimitException(AppException):
    """请求频率超限"""

    def __init__(
        self, detail: str = "请求过于频繁，请稍后重试", error_code: str = "RATE_LIMITED"
    ):
        super().__init__(status_code=429, detail=detail, error_code=error_code)
