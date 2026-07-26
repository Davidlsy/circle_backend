import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from app.config import get_settings, get_cors_origins

# ─── 日志初始化（在导入其他模块之前） ───
from app.logging_config import logger

settings = get_settings()

# 获取 CORS 允许的源列表（会验证配置安全性）
cors_origins = get_cors_origins()

from app.database import engine, Base
from app.schemas import Msg
from app.routers.auth_router import router as auth_router
from app.routers.post_router import router as post_router
from app.routers.follow_router import router as follow_router
from app.routers.message_router import router as message_router
from app.routers.feed_router import router as feed_router
from app.routers.tag_router import router as tag_router
from app.routers.audit_router import router as audit_router
from app.routers.group_router import router as group_router
from app.routers.star_router import router as star_router
from app.routers.discipline_router import router as discipline_router
from app.routers.report_router import router as report_router
from app.routers.checkin_router import router as checkin_router
from app.routers.fan_circle_router import router as fan_circle_router
from app.routers.fan_badge_router import router as fan_badge_router
from app.routers.user_router import router as user_router
from app.routers.circle_photo_router import router as circle_photo_router
from app.routers.sticker_router import router as sticker_router
# v2 新增：第三方登录 OAuth 路由
from app.routers.oauth_router import router as oauth_router
from app.routers.mock_oauth_router import router as mock_oauth_router
from app.error_handlers import register_exception_handlers

# 创建所有表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="粉丝社群平台 API",
    description="MVP 后端接口",
    version="1.0.66",
)

# ─── 注册全局异常处理器 ───
register_exception_handlers(app)

# ─── 请求日志中间件 ───
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """记录每个请求的耗时和状态码"""
    start_time = time.time()

    # 处理请求
    response = await call_next(request)

    # 计算耗时
    process_time = (time.time() - start_time) * 1000

    # 使用 loguru 记录访问日志
    logger.access(
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=process_time,
        client=request.client.host if request.client else "unknown",
    )

    # 在响应头中添加耗时
    response.headers["X-Process-Time"] = f"{process_time:.1f}ms"
    return response

# CORS 中间件配置
# 注意：cors_origins 已通过 get_cors_origins() 验证，确保生产环境配置了安全的来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["X-Process-Time"],
    max_age=600,  # 预检请求缓存 10 分钟
)

# 注册路由
app.include_router(auth_router)
app.include_router(post_router)
app.include_router(follow_router)
app.include_router(message_router)
app.include_router(feed_router)
app.include_router(tag_router)
app.include_router(audit_router)
app.include_router(group_router)
app.include_router(star_router)
app.include_router(discipline_router)
app.include_router(report_router)
app.include_router(checkin_router)
app.include_router(fan_circle_router)
app.include_router(fan_badge_router)
app.include_router(user_router)
app.include_router(circle_photo_router)
app.include_router(sticker_router)
# v2 新增：第三方登录 OAuth 路由
app.include_router(oauth_router)
app.include_router(mock_oauth_router)

# 静态文件：上传的图片（开发环境）
# 生产环境建议使用 Nginx 或 CDN 代理
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# ─── 健康检查 ───

@app.get("/", tags=["健康"])
def root():
    return {"msg": "粉丝社群平台 API 正常运行中"}


@app.get("/health", tags=["健康"])
def health():
    return {"status": "ok"}
