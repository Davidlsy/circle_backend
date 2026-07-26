"""
结构化日志配置 - 使用 loguru

功能：
- 请求日志：记录每个请求的详细信息
- 错误日志：记录异常和错误信息
- 慢查询日志：记录执行时间超过阈值的 SQL 查询
- 支持文件轮转和日志级别过滤
"""
import sys
import os
from pathlib import Path
from loguru import logger as loguru_logger


# ─── 日志配置 ───

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
SLOW_QUERY_THRESHOLD_MS = int(os.getenv("SLOW_QUERY_THRESHOLD_MS", "500"))

# 确保日志目录存在
LOG_DIR.mkdir(exist_ok=True)

# 日志格式
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# 移除默认 handler
loguru_logger.remove()

# ─── 控制台输出 ───
loguru_logger.add(
    sys.stdout,
    level=LOG_LEVEL,
    format=LOG_FORMAT,
    colorize=True,
)

# ─── 请求日志文件 ───
loguru_logger.add(
    LOG_DIR / "access.log",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    rotation="10 MB",
    retention="7 days",
    compression="zip",
    filter=lambda record: record["extra"].get("type") == "access",
)

# ─── 错误日志文件 ───
loguru_logger.add(
    LOG_DIR / "error.log",
    level="ERROR",
    format=LOG_FORMAT,
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    backtrace=True,
    diagnose=True,
)

# ─── 慢查询日志文件 ───
loguru_logger.add(
    LOG_DIR / "slow_query.log",
    level="WARNING",
    format="{time:YYYY-MM-DD HH:mm:ss} | {message}",
    rotation="10 MB",
    retention="7 days",
    compression="zip",
    filter=lambda record: record["extra"].get("type") == "slow_query",
)


# ─── 应用日志器 ───

class AppLogger:
    """应用日志器，提供结构化日志接口"""

    @staticmethod
    def info(message: str, **kwargs):
        """记录 INFO 级别日志"""
        loguru_logger.info(message, **kwargs)

    @staticmethod
    def warning(message: str, **kwargs):
        """记录 WARNING 级别日志"""
        loguru_logger.warning(message, **kwargs)

    @staticmethod
    def error(message: str, **kwargs):
        """记录 ERROR 级别日志"""
        loguru_logger.error(message, **kwargs)

    @staticmethod
    def debug(message: str, **kwargs):
        """记录 DEBUG 级别日志"""
        loguru_logger.debug(message, **kwargs)

    @staticmethod
    def access(method: str, path: str, status: int, duration_ms: float, client: str):
        """记录请求访问日志"""
        loguru_logger.bind(type="access").info(
            f"{method} {path} | status={status} | time={duration_ms:.1f}ms | client={client}"
        )

    @staticmethod
    def slow_query(sql: str, duration_ms: float, params: dict = None):
        """记录慢查询日志"""
        if duration_ms >= SLOW_QUERY_THRESHOLD_MS:
            loguru_logger.bind(type="slow_query").warning(
                f"SLOW QUERY | time={duration_ms:.1f}ms | sql={sql[:200]}... | params={params}"
            )

    @staticmethod
    def exception(message: str, **kwargs):
        """记录异常信息（含堆栈）"""
        loguru_logger.exception(message, **kwargs)


# 导出应用日志器
logger = AppLogger()
