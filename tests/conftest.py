"""
测试配置模块 - conftest.py

提供测试数据库、测试客户端和公共 fixtures。
每个测试函数使用独立的数据库会话，测试之间完全隔离。
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password, create_access_token

# ─── 确保所有模型在导入 Base 之前注册 ───
import app.models  # noqa: F401
from app.database import Base, get_db

# ─── 测试数据库（使用内存 SQLite，StaticPool 确保连接共享） ───

TEST_DATABASE_URL = "sqlite:///:memory:"

_test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

# SQLite 默认不启用外键约束，需要手动开启
@event.listens_for(_test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

_TestSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=_test_engine
)


def override_get_db():
    """替代生产数据库依赖，使用测试数据库"""
    db = _TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── 全局 fixtures ───

@pytest.fixture(autouse=True)
def setup_test_database():
    """
    每个测试前创建所有表，测试后清理。
    确保测试之间完全隔离。
    """
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


@pytest.fixture
def db():
    """获取一个测试数据库会话"""
    session = _TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """FastAPI 测试客户端（注入测试数据库）"""
    from app.main import app
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def auth_headers(db):
    """获取一个已认证用户的请求头"""
    from app.models import User

    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("password123"),
        nickname="Test User",
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": user.id})
    headers = {"Authorization": f"Bearer {token}"}

    yield headers, user.id


@pytest.fixture
def admin_headers(db):
    """获取一个管理员用户的请求头"""
    from app.models import User

    admin = User(
        username="admin",
        email="admin@example.com",
        hashed_password=hash_password("admin123"),
        nickname="Admin",
        is_active=True,
        is_superuser=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    token = create_access_token(data={"sub": admin.id})
    headers = {"Authorization": f"Bearer {token}"}

    yield headers, admin.id


@pytest.fixture
def registered_user(client):
    """注册一个普通用户并返回用户信息"""
    response = client.post("/auth/register", json={
        "username": "newuser",
        "password": "password123",
        "email": "newuser@example.com",
        "nickname": "New User",
    })
    return response


@pytest.fixture
def registered_user_token(client, registered_user):
    """注册用户并获取 token"""
    response = client.post("/auth/login", data={
        "username": "newuser",
        "password": "password123",
    })
    return response.json()["access_token"]
