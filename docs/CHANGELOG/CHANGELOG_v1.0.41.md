# 更新日志 v1.0.41

## 版本信息
- **版本号**: v1.0.41
- **发布日期**: 2026-05-14
- **更新类型**: 功能新增

## 更新概述

本次更新新增**评论点赞功能**，用户可以对帖子中的评论进行点赞/取消点赞，评论列表返回点赞数和当前用户点赞状态。

---

## 新增功能

### 1. 评论点赞

#### 1.1 数据模型

新增 `CommentLike` 模型：

```python
class CommentLike(Base):
    """评论点赞表"""
    __tablename__ = "comment_likes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    comment_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "comment_id", name="uq_comment_like_user_comment"),
        Index("ix_commentlike_comment_user", "comment_id", "user_id"),
        Index("ix_commentlike_user_comment", "user_id", "comment_id"),
    )
```

#### 1.2 API 接口

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 评论点赞 | POST | `/posts/comments/{id}/like` | 点赞或取消点赞 | 登录 |

#### 1.3 接口详情

- **路径**: `POST /posts/comments/{comment_id}/like`
- **功能**:
  - 已点赞 → 取消点赞
  - 未点赞 → 添加点赞
- **返回**:
  ```json
  {
    "msg": "已点赞",
    "is_liked": true,
    "like_count": 5
  }
  ```

#### 1.4 评论列表更新

评论列表现在返回点赞信息：

```json
{
  "id": 1,
  "content": "评论内容",
  "author": { "id": 1, "username": "user1" },
  "like_count": 5,
  "is_liked": true,
  "created_at": "2026-05-14T10:00:00"
}
```

- `like_count`: 该评论的点赞总数
- `is_liked`: 当前登录用户是否点赞（未登录时为 `false`）

#### 1.5 新增 Schema

```python
class CommentWithAuthor(CommentPublic):
    author: UserPublic
    like_count: int = 0      # 新增：评论点赞数
    is_liked: bool = False   # 新增：当前用户是否点赞

class CommentLikeResponse(BaseModel):
    msg: str
    is_liked: bool
    like_count: int
```

---

### 2. 可选认证依赖

新增 `get_current_active_user_optional()` 函数：

```python
async def get_current_active_user_optional(...) -> Optional[User]:
    """
    可选认证：已登录返回用户对象，未登录返回 None。
    用于评论列表等需要区分登录/未登录用户状态的场景。
    """
```

**用途**: 评论列表为公开接口，未登录用户也可查看，但需要区分是否显示点赞状态。

---

## 文件变更

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/models.py` | 新增 CommentLike 模型，Comment 添加 likes 关系 |
| `app/schemas.py` | CommentWithAuthor 添加 like_count/is_liked，新增 CommentLikeResponse |
| `app/auth.py` | 新增 get_current_active_user_optional() 可选认证依赖 |
| `app/routers/post_router.py` | 新增评论点赞接口，评论列表返回点赞信息 |
| `app/main.py` | 更新版本号至 1.0.41 |

---

## 数据库迁移

需要执行数据库迁移创建新表：

```bash
alembic revision --autogenerate -m "add_comment_like_table"
alembic upgrade head
```

---

## 使用示例

### 点赞评论
```bash
curl -X POST "http://localhost:8000/posts/comments/1/like" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 查看评论列表（含点赞信息）
```bash
curl "http://localhost:8000/posts/123/comments"
```

---

## 性能优化

评论列表使用批量查询获取点赞信息，避免 N+1 问题：
- 批量查询所有评论的点赞数（1 次 GROUP BY 查询）
- 批量查询当前用户点赞状态（1 次 IN 查询）

---

## 验证清单

- [x] CommentLike 数据模型
- [x] 点赞去重唯一约束
- [x] 复合索引优化
- [x] 评论点赞/取消点赞接口
- [x] 评论列表返回点赞数
- [x] 评论列表返回当前用户点赞状态
- [x] 可选认证依赖（未登录也能查看评论）
- [x] 批量查询优化
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
