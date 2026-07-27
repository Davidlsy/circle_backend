import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings, BASE_DIR, is_absolute_path

settings = get_settings()


def resolve_sqlite_db_path(database_url: str) -> str:
    """
    解析 SQLite 数据库文件的绝对路径

    通过动态计算 BASE_DIR 确保路径始终正确，不受启动时工作目录影响。

    Args:
        database_url: SQLite 数据库 URL

    Returns:
        str: 数据库文件的绝对路径
    """
    if not database_url.startswith("sqlite:///") or ":memory:" in database_url:
        return ""

    path_part = database_url[len("sqlite:///"):]

    if is_absolute_path(path_part):
        return os.path.normpath(path_part)

    abs_path = os.path.normpath(os.path.join(BASE_DIR, path_part))
    return abs_path


# 确保 SQLite 数据库目录存在
_db_path = resolve_sqlite_db_path(settings.DATABASE_URL)
if _db_path:
    _db_dir = os.path.dirname(_db_path)
    if _db_dir:
        os.makedirs(_db_dir, exist_ok=True)

# SQLite 专用连接参数；MySQL/PostgreSQL 等不需要
_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """依赖注入：每个请求一个独立的数据库 session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
