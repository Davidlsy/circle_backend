import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()

# 提取 SQLite 文件路径并确保其所在目录存在
# 仅对 SQLite 文件数据库生效（内存数据库 sqlite:///:memory: 跳过）
_db_url = settings.DATABASE_URL
if _db_url.startswith("sqlite:///") and ":memory:" not in _db_url:
    # 兼容 sqlite:///path 与 sqlite:////absolute/path 两种形式
    _db_file_path = _db_url.replace("sqlite:///", "", 1)
    # 处理 sqlite:////abs/path 形式：replace 后剩 "/abs/path"，已是绝对路径
    if _db_file_path.startswith("/"):
        _db_dir = os.path.dirname(_db_file_path)
    else:
        # 相对路径基于项目根目录解析（理论上 normalize_sqlite_database_url 已规范化）
        _db_dir = os.path.dirname(os.path.abspath(_db_file_path))
    if _db_dir:
        os.makedirs(_db_dir, exist_ok=True)

# SQLite 专用连接参数；MySQL/PostgreSQL 等不需要
_connect_args = {"check_same_thread": False} if _db_url.startswith("sqlite") else {}

engine = create_engine(
    _db_url,
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
