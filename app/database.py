import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()

# 确保 data/ 目录存在（数据库文件存放目录）
_db_dir = os.path.dirname(settings.DATABASE_URL.replace("sqlite:///", ""))
if _db_dir:
    os.makedirs(_db_dir, exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite 专用
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
