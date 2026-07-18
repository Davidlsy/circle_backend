# 更新日志 v1.0.45

## 版本信息
- **版本号**: v1.0.45
- **发布日期**: 2026-05-14
- **更新类型**: 功能新增

## 更新概述

本次更新新增**明星模块**，支持创建明星资料档案、明星单独帖子板块、明星排行榜（按粉丝数、热度、帖子数排序）。

---

## 新增功能

### 1. 明星资料管理

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 创建明星 | POST | `/stars/` | 创建明星资料 | 管理员 |
| 明星列表 | GET | `/stars/` | 获取明星列表（支持搜索） | 公开 |
| 明星详情 | GET | `/stars/{id}` | 获取明星详细信息 | 公开 |
| 更新明星 | PUT | `/stars/{id}` | 更新明星资料 | 管理员 |
| 删除明星 | DELETE | `/stars/{id}` | 删除明星（软删除） | 管理员 |

#### 1.1 明星资料字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 明星姓名（必填） |
| `avatar` | string | 头像 URL |
| `cover_image` | string | 封面图 URL |
| `description` | text | 简介 |
| `birthday` | datetime | 生日 |
| `gender` | string | 性别：男/女/其他 |
| `nationality` | string | 国籍 |
| `profession` | string | 职业 |
| `debut_date` | datetime | 出道日期 |
| `agency` | string | 经纪公司 |
| `social_links` | text | 社交链接（JSON） |
| `fan_count` | int | 粉丝数（冗余） |
| `post_count` | int | 帖子数（冗余） |
| `heat_score` | int | 热度分数 |
| `is_active` | bool | 是否启用 |

#### 1.2 创建明星示例

```bash
curl -X POST "http://localhost:8000/stars/" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "张三",
    "avatar": "/uploads/avatar.jpg",
    "description": "知名演员",
    "gender": "男",
    "profession": "演员",
    "agency": "某某娱乐"
  }'
```

---

### 2. 明星帖子板块

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 发布帖子 | POST | `/stars/{id}/posts` | 在明星板块发布帖子 | 登录 |
| 帖子列表 | GET | `/stars/{id}/posts` | 获取明星的帖子列表 | 公开 |

#### 2.1 发布明星帖子

- **路径**: `POST /stars/{id}/posts`
- **功能**: 创建帖子并自动关联到明星
- **请求体**: 与普通帖子相同

```json
{
  "title": "关于张三的讨论",
  "content": "这是内容...",
  "content_format": "markdown",
  "is_published": true
}
```

#### 2.2 帖子关联

- 帖子通过 `StarPost` 关联表与明星关联
- 一个帖子可以关联多个明星（未来扩展）
- 发布帖子后自动更新明星的 `post_count`

---

### 3. 明星排行榜

| 接口 | 方法 | 路径 | 功能说明 |
|------|------|------|----------|
| 粉丝榜 | GET | `/stars/ranking/fans` | 按粉丝数排序 |
| 热度榜 | GET | `/stars/ranking/heat` | 按热度分数排序 |
| 帖子榜 | GET | `/stars/ranking/posts` | 按帖子数排序 |

#### 3.1 排行榜参数

- `limit`: 返回数量（默认 20，最大 100）

#### 3.2 排行榜返回

```json
[
  {
    "rank": 1,
    "star": {
      "id": 1,
      "name": "张三",
      "avatar": "/uploads/avatar.jpg",
      ...
    },
    "fan_count": 10000,
    "post_count": 500,
    "heat_score": 9999
  }
]
```

---

## 数据模型

### 新增模型

| 模型 | 说明 | 主要字段 |
|------|------|----------|
| Star | 明星资料 | name, avatar, description, fan_count, post_count, heat_score |
| StarPost | 明星帖子关联 | star_id, post_id |

### 索引优化

| 索引 | 说明 |
|------|------|
| `uq_star_post` | 明星ID+帖子ID 唯一约束 |
| `ix_starpost_star` | 明星ID+创建时间 复合索引（快速查询明星帖子） |

---

## 文件变更

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `app/routers/star_router.py` | 明星路由（13 个接口） |

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/models.py` | 新增 Star、StarPost 模型 |
| `app/schemas.py` | 新增明星相关 Schema（8 个） |
| `app/main.py` | 注册明星路由，更新版本号至 1.0.45 |

---

## 数据库迁移

```bash
alembic revision --autogenerate -m "add_star_tables"
alembic upgrade head
```

**新增表**:
- `stars` - 明星资料表
- `star_posts` - 明星帖子关联表

---

## API 统计

| 模块 | 原接口数 | 新接口数 | 总计 |
|------|----------|----------|------|
| 明星模块 | 0 | 13 | 13 |
| **项目总计** | 67 | 13 | **80** |

---

## 使用示例

### 创建明星
```bash
curl -X POST "http://localhost:8000/stars/" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "李四", "profession": "歌手"}'
```

### 搜索明星
```bash
curl "http://localhost:8000/stars/?keyword=张&page=1&page_size=10"
```

### 发布明星帖子
```bash
curl -X POST "http://localhost:8000/stars/1/posts" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "讨论帖", "content": "内容..."}'
```

### 获取明星帖子
```bash
curl "http://localhost:8000/stars/1/posts"
```

### 查看排行榜
```bash
# 粉丝榜
curl "http://localhost:8000/stars/ranking/fans?limit=10"

# 热度榜
curl "http://localhost:8000/stars/ranking/heat?limit=10"

# 帖子榜
curl "http://localhost:8000/stars/ranking/posts?limit=10"
```

---

## 安全特性

| 特性 | 说明 |
|------|------|
| 权限控制 | 仅管理员可创建/修改/删除明星资料 |
| 软删除 | 删除明星时设置 is_active=False，保留数据 |
| 搜索过滤 | 仅返回 is_active=True 的明星 |

---

## 验证清单

- [x] Star 数据模型
- [x] StarPost 关联模型（唯一约束+索引）
- [x] 创建明星资料
- [x] 明星列表（支持搜索）
- [x] 明星详情
- [x] 更新明星资料
- [x] 删除明星（软删除）
- [x] 明星帖子发布
- [x] 明星帖子列表
- [x] 粉丝数排行榜
- [x] 热度排行榜
- [x] 帖子数排行榜
- [x] 管理员权限控制
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
