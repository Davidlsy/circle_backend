# 更新日志 v1.0.46

## 版本信息
- **版本号**: v1.0.46
- **发布日期**: 2026-05-14
- **更新类型**: 功能变更（破坏性变更）

## 更新概述

本次更新将所有帖子与明星强制关联，**创建帖子时必须指定明星**。帖子列表和详情现在返回关联的明星信息。

---

## 变更内容

### 1. 帖子创建 API 变更

**创建帖子现在必须提供 `star_id`**：

```json
{
  "title": "帖子标题",
  "content": "帖子内容",
  "content_format": "markdown",
  "is_published": true,
  "star_id": 1  // 必填：关联的明星ID
}
```

**错误响应**（明星不存在时）：
```json
{
  "detail": "明星不存在或已禁用"
}
```

### 2. 帖子返回数据变更

帖子列表和详情现在返回 `star` 字段：

```json
{
  "id": 123,
  "title": "帖子标题",
  "content": "内容...",
  "star": {  // 新增：关联的明星信息
    "id": 1,
    "name": "张三",
    "avatar": "/uploads/avatar.jpg",
    "profession": "演员",
    ...
  },
  "author": {...},
  "comment_count": 10,
  ...
}
```

### 3. 创建帖子流程变更

**原流程**：
1. 创建帖子 → 返回帖子

**新流程**：
1. 验证明星是否存在且启用
2. 创建帖子
3. 关联帖子到明星（StarPost 表）
4. 更新明星帖子数
5. 返回帖子（包含明星信息）

---

## 文件变更

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/schemas.py` | PostCreate 添加必填 star_id；PostDetail 添加 star 字段 |
| `app/routers/post_router.py` | 创建帖子强制关联明星；列表/详情返回明星信息 |
| `app/main.py` | 更新版本号至 1.0.46 |

---

## API 变更详情

### POST /posts/ - 创建帖子

**请求体变更**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `star_id` | int | ✅ 是 | 关联的明星ID |

**完整请求示例**：
```bash
curl -X POST "http://localhost:8000/posts/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "关于张三的讨论",
    "content": "这是内容...",
    "content_format": "markdown",
    "is_published": true,
    "star_id": 1
  }'
```

### GET /posts/ - 帖子列表

**响应变更**：每个帖子新增 `star` 字段

### GET /posts/{id} - 帖子详情

**响应变更**：新增 `star` 字段

---

## 数据库影响

- 所有新创建的帖子都会关联到 StarPost 表
- 明星的 `post_count` 会自动更新
- 现有帖子（如有）不会自动关联明星，需要手动处理

---

## 迁移建议

### 现有数据处理

如果已有帖子数据，需要迁移：

```python
# 示例：将现有帖子关联到默认明星
def migrate_existing_posts():
    default_star_id = 1  # 默认明星ID
    posts = db.query(Post).all()
    for post in posts:
        # 检查是否已关联
        existing = db.query(StarPost).filter(StarPost.post_id == post.id).first()
        if not existing:
            star_post = StarPost(star_id=default_star_id, post_id=post.id)
            db.add(star_post)
    db.commit()
```

---

## 验证清单

- [x] PostCreate Schema 添加必填 star_id
- [x] PostDetail Schema 添加 star 字段
- [x] 创建帖子时验证明星存在
- [x] 创建帖子时自动关联明星
- [x] 创建帖子时更新明星帖子数
- [x] 帖子列表返回明星信息（批量查询优化）
- [x] 帖子详情返回明星信息
- [x] 更新版本号

---

## 破坏性变更说明

⚠️ **此版本包含破坏性变更**：

1. **创建帖子 API**：现在必须提供 `star_id` 字段
2. **前端适配**：需要修改帖子创建界面，添加明星选择
3. **现有数据**：未关联明星的帖子不会显示明星信息

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
