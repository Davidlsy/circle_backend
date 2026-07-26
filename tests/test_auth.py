"""
认证模块单元测试

覆盖范围：
- 用户注册（正常注册、重复用户名、重复邮箱、重复手机号、参数校验）
- 用户登录（正常登录、用户名或邮箱登录、密码错误、用户不存在）
- 找回密码（正常流程、用户不存在防枚举、验证码过期、验证码已使用）
- 重置密码（正常重置、无效验证码、密码格式校验）
- Token 工具函数（创建/解析、无效 token、密码哈希）
"""
import pytest
from app.auth import hash_password, verify_password, create_access_token, decode_token


# ═══════════════════════════════════════════════════════
# 一、用户注册测试
# ═══════════════════════════════════════════════════════

class TestRegister:
    """用户注册接口测试"""

    def test_register_success(self, client):
        """正常注册"""
        response = client.post("/auth/register", json={
            "username": "alice",
            "password": "password123",
            "email": "alice@example.com",
            "nickname": "Alice",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "alice"
        assert data["nickname"] == "Alice"
        assert data["is_superuser"] is False
        assert "id" in data
        assert "created_at" in data

    def test_register_duplicate_username(self, client):
        """重复用户名应返回 400"""
        client.post("/auth/register", json={
            "username": "bob",
            "password": "password123",
        })
        response = client.post("/auth/register", json={
            "username": "bob",
            "password": "different456",
        })
        assert response.status_code == 400
        assert "用户名已被注册" in response.json()["detail"]

    def test_register_duplicate_email(self, client):
        """重复邮箱应返回 400"""
        client.post("/auth/register", json={
            "username": "user1",
            "password": "password123",
            "email": "same@example.com",
        })
        response = client.post("/auth/register", json={
            "username": "user2",
            "password": "password123",
            "email": "same@example.com",
        })
        assert response.status_code == 400
        assert "邮箱已被注册" in response.json()["detail"]

    def test_register_duplicate_phone(self, client):
        """重复手机号应返回 400"""
        client.post("/auth/register", json={
            "username": "user1",
            "password": "password123",
            "phone": "13800138000",
        })
        response = client.post("/auth/register", json={
            "username": "user2",
            "password": "password123",
            "phone": "13800138000",
        })
        assert response.status_code == 400
        assert "手机号已被注册" in response.json()["detail"]

    def test_register_username_too_short(self, client):
        """用户名太短应返回 422"""
        response = client.post("/auth/register", json={
            "username": "ab",
            "password": "password123",
        })
        assert response.status_code == 422

    def test_register_password_too_short(self, client):
        """密码太短应返回 422"""
        response = client.post("/auth/register", json={
            "username": "validname",
            "password": "12345",
        })
        assert response.status_code == 422

    def test_register_missing_username(self, client):
        """缺少用户名应返回 422"""
        response = client.post("/auth/register", json={
            "password": "password123",
        })
        assert response.status_code == 422

    def test_register_missing_password(self, client):
        """缺少密码应返回 422"""
        response = client.post("/auth/register", json={
            "username": "validname",
        })
        assert response.status_code == 422

    def test_register_nickname_defaults_to_username(self, client):
        """不提供 nickname 时应默认为 username"""
        response = client.post("/auth/register", json={
            "username": "defaultnick",
            "password": "password123",
        })
        assert response.status_code == 201
        assert response.json()["nickname"] == "defaultnick"

    def test_register_password_hashed(self, db):
        """注册后密码应被 bcrypt 哈希存储"""
        from app.models import User

        user = User(
            username="hashcheck",
            hashed_password=hash_password("mypassword"),
        )
        db.add(user)
        db.commit()

        stored = db.query(User).filter(User.username == "hashcheck").first()
        assert stored.hashed_password != "mypassword"
        assert verify_password("mypassword", stored.hashed_password) is True
        assert verify_password("wrongpassword", stored.hashed_password) is False


# ═══════════════════════════════════════════════════════
# 二、用户登录测试
# ═══════════════════════════════════════════════════════

class TestLogin:
    """用户登录接口测试"""

    def test_login_success(self, client, registered_user):
        """正常登录应返回 token"""
        response = client.post("/auth/login", data={
            "username": "newuser",
            "password": "password123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    def test_login_with_email(self, client, registered_user):
        """使用邮箱登录"""
        response = client.post("/auth/login", data={
            "username": "newuser@example.com",
            "password": "password123",
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_wrong_password(self, client, registered_user):
        """密码错误应返回 401"""
        response = client.post("/auth/login", data={
            "username": "newuser",
            "password": "wrongpassword",
        })
        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """用户不存在应返回 401"""
        response = client.post("/auth/login", data={
            "username": "nonexistent",
            "password": "password123",
        })
        assert response.status_code == 401

    def test_login_empty_fields(self, client):
        """空字段应返回 401（OAuth2 表单校验）"""
        response = client.post("/auth/login", data={
            "username": "",
            "password": "",
        })
        # OAuth2 表单提交空字段时，后端会查询空用户名返回 401
        assert response.status_code == 401

    def test_login_returns_valid_jwt(self, client, registered_user, registered_user_token):
        """登录返回的 JWT 应包含正确的用户信息"""
        token_data = decode_token(registered_user_token)
        assert token_data is not None
        assert token_data.user_id is not None


# ═══════════════════════════════════════════════════════
# 三、找回密码测试
# ═══════════════════════════════════════════════════════

class TestForgotPassword:
    """找回密码接口测试"""

    def test_forgot_password_existing_user(self, client, registered_user):
        """已注册用户应返回验证码"""
        response = client.post("/auth/forgot-password", json={
            "username": "newuser",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["msg"] == "如果账号存在，验证码已生成"
        assert len(data["code"]) == 6
        assert data["code"].isdigit()
        assert data["expires_in_seconds"] == 900  # 15 分钟

    def test_forgot_password_with_email(self, client, registered_user):
        """使用邮箱找回密码"""
        response = client.post("/auth/forgot-password", json={
            "username": "newuser@example.com",
        })
        assert response.status_code == 200
        assert len(response.json()["code"]) == 6

    def test_forgot_password_nonexistent_user(self, client):
        """不存在的用户也应返回成功（防枚举）"""
        response = client.post("/auth/forgot-password", json={
            "username": "nonexistent",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["msg"] == "如果账号存在，验证码已生成"
        # 不存在的用户返回占位验证码
        assert data["code"] == "------"

    def test_forgot_password_invalidates_old_codes(self, client, registered_user):
        """多次请求应作废旧验证码"""
        # 第一次请求
        resp1 = client.post("/auth/forgot-password", json={"username": "newuser"})
        code1 = resp1.json()["code"]

        # 第二次请求
        resp2 = client.post("/auth/forgot-password", json={"username": "newuser"})
        code2 = resp2.json()["code"]

        # 旧验证码应已失效
        response = client.post("/auth/reset-password", json={
            "code": code1,
            "new_password": "newpassword123",
        })
        assert response.status_code == 400

        # 新验证码应该有效
        response = client.post("/auth/reset-password", json={
            "code": code2,
            "new_password": "newpassword123",
        })
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════
# 四、重置密码测试
# ═══════════════════════════════════════════════════════

class TestResetPassword:
    """重置密码接口测试"""

    def test_reset_password_success(self, client, registered_user):
        """正常重置密码流程"""
        # 1. 获取验证码
        resp = client.post("/auth/forgot-password", json={"username": "newuser"})
        code = resp.json()["code"]

        # 2. 使用验证码重置密码
        response = client.post("/auth/reset-password", json={
            "code": code,
            "new_password": "newpassword456",
        })
        assert response.status_code == 200
        assert "密码重置成功" in response.json()["msg"]

        # 3. 使用新密码登录
        login_resp = client.post("/auth/login", data={
            "username": "newuser",
            "password": "newpassword456",
        })
        assert login_resp.status_code == 200

        # 4. 旧密码应失效
        old_login_resp = client.post("/auth/login", data={
            "username": "newuser",
            "password": "password123",
        })
        assert old_login_resp.status_code == 401

    def test_reset_password_invalid_code(self, client):
        """无效验证码应返回 400"""
        response = client.post("/auth/reset-password", json={
            "code": "000000",
            "new_password": "newpassword123",
        })
        assert response.status_code == 400
        assert "验证码无效或已过期" in response.json()["detail"]

    def test_reset_password_code_too_short(self, client):
        """验证码格式错误应返回 422"""
        response = client.post("/auth/reset-password", json={
            "code": "12345",
            "new_password": "newpassword123",
        })
        assert response.status_code == 422

    def test_reset_password_new_password_too_short(self, client):
        """新密码太短应返回 422"""
        response = client.post("/auth/reset-password", json={
            "code": "123456",
            "new_password": "12345",
        })
        assert response.status_code == 422

    def test_reset_password_code_single_use(self, client, registered_user):
        """验证码一次性使用"""
        # 获取验证码
        resp = client.post("/auth/forgot-password", json={"username": "newuser"})
        code = resp.json()["code"]

        # 第一次使用
        response1 = client.post("/auth/reset-password", json={
            "code": code,
            "new_password": "newpassword111",
        })
        assert response1.status_code == 200

        # 第二次使用同一验证码
        response2 = client.post("/auth/reset-password", json={
            "code": code,
            "new_password": "newpassword222",
        })
        assert response2.status_code == 400


# ═══════════════════════════════════════════════════════
# 五、Token 工具函数测试
# ═══════════════════════════════════════════════════════

class TestTokenUtils:
    """JWT Token 工具函数测试"""

    def test_create_and_decode_token(self):
        """创建和解析 token"""
        token = create_access_token(data={"sub": 42})
        token_data = decode_token(token)
        assert token_data is not None
        assert token_data.user_id == 42

    def test_decode_invalid_token(self):
        """解析无效 token 应返回 None"""
        token_data = decode_token("invalid.token.here")
        assert token_data is None

    def test_decode_empty_token(self):
        """解析空 token 应返回 None"""
        token_data = decode_token("")
        assert token_data is None

    def test_hash_and_verify_password(self):
        """密码哈希和验证"""
        hashed = hash_password("my_secret_password")
        assert hashed != "my_secret_password"
        assert verify_password("my_secret_password", hashed) is True
        assert verify_password("wrong_password", hashed) is False

    def test_different_passwords_different_hashes(self):
        """不同密码应产生不同哈希"""
        hash1 = hash_password("password1")
        hash2 = hash_password("password2")
        assert hash1 != hash2
