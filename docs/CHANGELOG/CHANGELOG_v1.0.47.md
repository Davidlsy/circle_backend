# 更新日志 v1.0.47

## 版本信息
- **版本号**: v1.0.47
- **发布日期**: 2026-05-14
- **更新类型**: 功能新增

## 更新概述

本次更新新增**粉丝模块**，支持用户关注/取消关注明星，一个用户可以成为多个明星的粉丝，一个明星可以有多个粉丝。

---

## 新增功能

### 1. 关注/取消关注明星

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 关注/取消 | POST | `/stars/{id}/follow` | 关注或取消关注明星 | 登录 |

#### 1.1 接口详情

- **路径**: `POST /stars/{star_id}/follow`
- **功能**:
  - 已关注 → 取消关注
  - 未关注 → 添加关注
- **返回**:
  ```json
  {
    "msg": "已关注",
    "is_following": true,
    "fan_count": 1000
  }
  ```

#### 1.2 自动更新粉丝数

关注/取消关注时会自动更新明星的 `fan_count` 字段。

---

### 2. 粉丝列表

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 粉丝列表 | GET | `/stars/{id}/followers` | 获取明星的粉丝列表 | 公开 |

#### 2.1 接口详情

- **路径**: `GET /stars/{star_id}/followers`
- **查询参数**:
  - `page`: 页码（默认 1）
  - `page_size`: 每页数量（默认 20，最大 100）
- **返回**:
  ```json
  [
    {
      "id": 1,
      "star_id": 1,
      "user_id": 2,
      "created_at": "2026-05-14T10:00:00",
      "user": {
        "id": 2,
        "username": "user2",
        "nickname": "用户2"
      }
    }
  ]
  ```

---

### 3. 关注状态查询

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 关注状态 | GET | `/stars/{id}/follow/status` | 检查是否已关注 | 登录 |

#### 3.1 接口详情

- **路径**: `GET /stars/{star_id}/follow/status`
- **返回**:
  ```json
  {
    "is_following": true
  }
  ```

---

### 4. 我关注的明星

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 我的关注 | GET | `/stars/users/me/following` | 获取我关注的明星列表 | 登录 |

#### 4.1 接口详情

- **路径**: `GET /stars/users/me/following`
- **查询参数**:
  - `page`: 页码（默认 1）
  - `page_size`: 每页数量（默认 20，最大 100）
- **返回**:
  ```json
  [
    {
      "id": 1,
      "star_id": 1,
      "user_id": 2,
      "created_at": "2026-05-14T10:00:00",
      "star": {
        "id": 1,
        "name": "张三",
        "avatar": "/uploads/avatar.jpg",
        "fan_count": 1000
      }
    }
  ]
  ```

---

## 数据模型

### 新增模型

| 模型 | 说明 | 主要字段 |
|------|------|----------|
| StarFollow | 明星粉丝关联 | star_id, user_id, created_at |

### 索引优化

| 索引 | 说明 |
|------|------|
| `uq_star_follow` | 明星ID+用户ID 唯一约束（防止重复关注） |
| `ix_starfollow_star` | 明星ID+创建时间（快速查询明星粉丝） |
| `ix_starfollow_user` | 用户ID+创建时间（快速查询用户关注） |

---

## 文件变更

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/models.py` | 新增 StarFollow 模型，Star 添加 followers 关系，User 添加 following_stars 关系 |
| `app/schemas.py` | 新增粉丝相关 Schema（3 个） |
| `app/routers/star_router.py` | 新增粉丝相关路由（4 个接口） |
| `app/main.py` | 更新版本号至 1.0.47 |

---

## 数据库迁移

```bash
alembic revision --autogenerate -m "add_star_follow_table"
alembic upgrade head
```

**新增表**:
- `star_follows` - 明星粉丝关联表

---

## API 统计

| 模块 | 原接口数 | 新接口数 | 总计 |
|------|----------|----------|------|
| 明星模块 | 13 | 4 | 17 |
| **项目总计** | 80 | 4 | **84** |

---

## 使用示例

### 关注明星
```bash
curl -X POST "http://localhost:8000/stars/1/follow" \
  -H "Authorization: Bearer YOUR_TOKEN"
# 返回: {"msg": "已关注", "is_following": true, "fan_count": 1001}
```

### 取消关注
```bash
curl -X POST "http://localhost:8000/stars/1/follow" \
  -H "Authorization: Bearer YOUR_TOKEN"
# 返回: {"msg": "已取消关注", "is_following": false, "fan_count": 1000}
```

### 获取粉丝列表
```bash
curl "http://localhost:8000/stars/1/followers?page=1&page_size=20"
```

### 检查关注状态
```bash
curl "http://localhost:8000/stars/1/follow/status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 获取我关注的明星
```bash
curl "http://localhost:8000/stars/users/me/following" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 验证清单

- [x] StarFollow 数据模型
- [x] 唯一约束（防止重复关注）
- [x] 复合索引优化
- [x] 关注/取消关注接口
- [x] 自动更新明星粉丝数
- [x] 粉丝列表接口
- [x] 关注状态查询接口
- [x] 我关注的明星列表接口
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
