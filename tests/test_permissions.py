"""
权限控制单元测试

覆盖范围：
- 未认证访问受保护接口（应返回 401）
- 无效 Token 访问（应返回 401）
- 普通用户访问管理员接口（应返回 403）
- 管理员访问管理员接口（应正常）
- 作者编辑自己的帖子（应正常）
- 用户编辑他人帖子（应返回 403）
- 用户删除自己的帖子（应正常）
- 普通用户删除他人帖子（应返回 403）
- 管理员删除任意帖子（应正常）
"""
import pytest
from app.auth import create_access_token, hash_password


def _create_user(db, username, email=None, is_superuser=False):
    """辅助方法：在测试数据库中直接创建用户"""
    from app.models import User
    user = User(
        username=username,
        email=email or f"{username}@example.com",
        hashed_password=hash_password("password123"),
        nickname=username,
        is_active=True,
        is_superuser=is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _get_auth_headers(user):
    """辅助方法：生成认证请求头"""
    token = create_access_token(data={"sub": user.id})
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════
# 一、认证保护测试
# ═══════════════════════════════════════════════════════

class TestAuthenticationRequired:
    """未认证访问受保护接口测试"""

    def test_get_my_profile_without_token(self, client):
        """未携带 Token 访问个人资料应返回 401"""
        response = client.get("/users/me")
        assert response.status_code == 401

    def test_update_profile_without_token(self, client):
        """未携带 Token 修改个人资料应返回 401"""
        response = client.patch("/users/me", json={"nickname": "hacked"})
        assert response.status_code == 401

    def test_create_post_without_token(self, client):
        """未携带 Token 创建帖子应返回 401"""
        response = client.post("/posts/", json={
            "title": "Test",
            "content": "Content",
        })
        assert response.status_code == 401

    def test_like_post_without_token(self, client):
        """未携带 Token 点赞应返回 401"""
        response = client.post("/posts/1/like")
        assert response.status_code == 401

    def test_follow_user_without_token(self, client):
        """未携带 Token 关注用户应返回 401"""
        response = client.post("/users/1/follow")
        assert response.status_code == 401

    def test_send_message_without_token(self, client):
        """未携带 Token 发送私信应返回 401"""
        response = client.post("/messages/conversations", json={
            "target_user_id": 2,
        })
        assert response.status_code == 401

    def test_invalid_token(self, client):
        """无效 Token 应返回 401"""
        response = client.get("/users/me", headers={
            "Authorization": "Bearer invalid.token.here"
        })
        assert response.status_code == 401

    def test_malformed_auth_header(self, client):
        """格式错误的 Authorization 头应返回 401"""
        response = client.get("/users/me", headers={
            "Authorization": "NotBearer sometoken"
        })
        assert response.status_code == 401

    def test_empty_bearer_token(self, client):
        """空的 Bearer Token 应返回 401"""
        response = client.get("/users/me", headers={
            "Authorization": "Bearer "
        })
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════
# 二、用户资料权限测试
# ═══════════════════════════════════════════════════════

class TestUserProfilePermission:
    """用户资料权限测试"""

    def test_get_own_profile(self, client, db):
        """获取自己的资料应正常"""
        user = _create_user(db, "profileuser")
        headers = _get_auth_headers(user)
        response = client.get("/users/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["username"] == "profileuser"

    def test_update_own_profile(self, client, db):
        """修改自己的资料应正常"""
        user = _create_user(db, "edituser")
        headers = _get_auth_headers(user)
        response = client.patch("/users/me", json={
            "nickname": "Updated Nickname",
            "bio": "Hello world",
        }, headers=headers)
        assert response.status_code == 200
        assert response.json()["nickname"] == "Updated Nickname"
        assert response.json()["bio"] == "Hello world"

    def test_get_public_profile_no_auth(self, client, db):
        """获取公开用户资料不需要认证"""
        user = _create_user(db, "publicuser")
        response = client.get(f"/users/{user.id}")
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════
# 三、帖子权限测试
# ═══════════════════════════════════════════════════════

class TestPostPermission:
    """帖子操作权限测试"""

    def test_author_can_edit_own_post(self, client, db):
        """作者可以编辑自己的帖子"""
        owner = _create_user(db, "owner_edit")
        headers = _get_auth_headers(owner)

        # 创建帖子
        post_resp = client.post("/posts/", json={
            "title": "我的帖子",
            "content": "帖子内容",
        }, headers=headers)
        post_id = post_resp.json()["id"]

        # 编辑自己的帖子
        response = client.put(f"/posts/{post_id}", json={
            "title": "修改后的标题",
        }, headers=headers)
        assert response.status_code == 200
        assert response.json()["title"] == "修改后的标题"

    def test_user_cannot_edit_others_post(self, client, db):
        """用户不能编辑他人的帖子"""
        owner = _create_user(db, "owner_edit2")
        other = _create_user(db, "other_edit2")

        # owner 创建帖子
        post_resp = client.post("/posts/", json={
            "title": "owner的帖子",
            "content": "内容",
        }, headers=_get_auth_headers(owner))
        post_id = post_resp.json()["id"]

        # other 尝试编辑
        response = client.put(f"/posts/{post_id}", json={
            "title": "试图修改",
        }, headers=_get_auth_headers(other))
        assert response.status_code == 403

    def test_author_can_delete_own_post(self, client, db):
        """作者可以删除自己的帖子"""
        owner = _create_user(db, "owner_del")
        headers = _get_auth_headers(owner)

        post_resp = client.post("/posts/", json={
            "title": "待删除帖子",
            "content": "内容",
        }, headers=headers)
        post_id = post_resp.json()["id"]

        response = client.delete(f"/posts/{post_id}", headers=headers)
        assert response.status_code == 200

    def test_user_cannot_delete_others_post(self, client, db):
        """普通用户不能删除他人的帖子"""
        owner = _create_user(db, "owner_del2")
        attacker = _create_user(db, "attacker_del2")

        post_resp = client.post("/posts/", json={
            "title": "owner的帖子",
            "content": "内容",
        }, headers=_get_auth_headers(owner))
        post_id = post_resp.json()["id"]

        response = client.delete(f"/posts/{post_id}", headers=_get_auth_headers(attacker))
        assert response.status_code == 403

    def test_admin_can_delete_any_post(self, client, db):
        """管理员可以删除任意帖子"""
        owner = _create_user(db, "normal_del")
        admin = _create_user(db, "admin_del", is_superuser=True)

        post_resp = client.post("/posts/", json={
            "title": "普通用户的帖子",
            "content": "内容",
        }, headers=_get_auth_headers(owner))
        post_id = post_resp.json()["id"]

        response = client.delete(f"/posts/{post_id}", headers=_get_auth_headers(admin))
        assert response.status_code == 200


# ═══════════════════════════════════════════════════════
# 四、管理员接口权限测试
# ═══════════════════════════════════════════════════════

class TestAdminPermission:
    """管理员接口权限测试"""

    def test_admin_can_access_pending_posts(self, client, db):
        """管理员可以查看待审核帖子列表"""
        admin = _create_user(db, "admin_pending", is_superuser=True)
        response = client.get("/admin/posts/pending", headers=_get_auth_headers(admin))
        assert response.status_code == 200

    def test_normal_user_cannot_access_admin_pending_posts(self, client, db):
        """普通用户不能查看待审核帖子列表"""
        normal = _create_user(db, "normal_pending")
        response = client.get("/admin/posts/pending", headers=_get_auth_headers(normal))
        assert response.status_code == 403

    def test_admin_can_approve_post(self, client, db):
        """管理员可以审核通过帖子"""
        poster = _create_user(db, "poster_audit")
        admin = _create_user(db, "admin_audit", is_superuser=True)

        # 创建帖子
        post_resp = client.post("/posts/", json={
            "title": "待审核帖子",
            "content": "内容",
        }, headers=_get_auth_headers(poster))
        post_id = post_resp.json()["id"]

        # 管理员审核通过
        response = client.post(f"/admin/posts/{post_id}/audit", json={
            "status": "approved",
        }, headers=_get_auth_headers(admin))
        assert response.status_code == 200
        assert response.json()["status"] == "approved"

    def test_normal_user_cannot_audit_post(self, client, db):
        """普通用户不能审核帖子"""
        poster = _create_user(db, "poster_audit2")
        normal = _create_user(db, "normal_audit2")

        post_resp = client.post("/posts/", json={
            "title": "帖子",
            "content": "内容",
        }, headers=_get_auth_headers(poster))
        post_id = post_resp.json()["id"]

        response = client.post(f"/admin/posts/{post_id}/audit", json={
            "status": "approved",
        }, headers=_get_auth_headers(normal))
        assert response.status_code == 403

    def test_unauthenticated_cannot_access_admin(self, client):
        """未认证用户不能访问管理员接口"""
        response = client.get("/admin/posts/pending")
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════
# 五、社交功能权限测试
# ═══════════════════════════════════════════════════════

class TestSocialPermission:
    """社交功能权限测试"""

    def test_follow_requires_auth(self, client):
        """关注需要认证"""
        response = client.post("/users/1/follow")
        assert response.status_code == 401

    def test_friends_list_requires_auth(self, client):
        """好友列表需要认证"""
        response = client.get("/users/me/friends")
        assert response.status_code == 401

    def test_conversation_requires_auth(self, client):
        """发起会话需要认证"""
        response = client.post("/messages/conversations", json={
            "target_user_id": 1,
        })
        assert response.status_code == 401

    def test_feed_requires_auth(self, client):
        """动态流需要认证"""
        response = client.get("/feed/")
        assert response.status_code == 401
