# 更新日志 v1.0.48

## 版本信息
- **版本号**: v1.0.48
- **发布日期**: 2026-05-14
- **更新类型**: 功能重构

## 更新概述

本次更新**重构粉丝模块**，将"关注"和"粉丝"明确区分为两个独立功能：

| 功能 | 说明 | 是否需要审核 |
|------|------|-------------|
| **关注** | 普通关注关系 | ❌ 无需审核 |
| **粉丝** | 官方粉丝身份 | ✅ 需要申请并审核 |

---

## 功能对比

### 关注（StarFollow）
- 用户可随时关注/取消关注明星
- 无需审核，即时生效
- 用于接收明星动态

### 粉丝（StarFan）- 新增申请-审核制
- 用户需要**申请**成为粉丝
- 明星管理员**审核**后才能成为正式粉丝
- 被拒绝后可以重新申请
- 粉丝身份更有荣誉感

---

## 新增功能

### 1. 申请成为粉丝

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 申请粉丝 | POST | `/stars/{id}/fans/apply` | 提交粉丝申请 | 登录 |

#### 1.1 接口详情

- **路径**: `POST /stars/{star_id}/fans/apply`
- **请求体**:
  ```json
  {
    "apply_message": "我是张三的忠实粉丝，希望能加入粉丝团"
  }
  ```
- **状态流转**:
  - 新申请 → `pending`（待审核）
  - 审核通过 → `approved`（已通过）
  - 审核拒绝 → `rejected`（已拒绝）
  - 被拒绝后可重新申请

#### 1.2 返回示例

```json
{
  "id": 1,
  "star_id": 1,
  "user_id": 2,
  "status": "pending",
  "apply_message": "我是张三的忠实粉丝...",
  "created_at": "2026-05-14T10:00:00",
  "user": {
    "id": 2,
    "username": "user2"
  }
}
```

---

### 2. 审核粉丝申请

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 查看待审核 | GET | `/stars/{id}/fans/pending` | 获取待审核列表 | 管理员 |
| 审核申请 | POST | `/stars/{id}/fans/{fan_id}/review` | 通过/拒绝申请 | 管理员 |

#### 2.1 查看待审核列表

- **路径**: `GET /stars/{star_id}/fans/pending`
- **权限**: 仅管理员

#### 2.2 审核申请

- **路径**: `POST /stars/{star_id}/fans/{fan_id}/review`
- **请求体**:
  ```json
  {
    "status": "approved",
    "review_message": "欢迎加入粉丝团！"
  }
  ```
- **status 可选值**: `approved`（通过）/ `rejected`（拒绝）

---

### 3. 粉丝列表

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 粉丝列表 | GET | `/stars/{id}/fans` | 获取已通过的粉丝 | 公开 |

- **路径**: `GET /stars/{star_id}/fans`
- **说明**: 仅返回 `status=approved` 的粉丝

---

### 4. 我的粉丝申请

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 我的申请 | GET | `/stars/users/me/fan-applications` | 查看我的所有申请 | 登录 |
| 取消申请 | DELETE | `/stars/{id}/fans/me` | 取消申请或退出粉丝 | 登录 |

#### 4.1 我的申请列表

- **路径**: `GET /stars/users/me/fan-applications`
- **查询参数**: `status`（可选：pending/approved/rejected）
- **返回**: 我申请的所有明星及状态

#### 4.2 取消粉丝身份

- **路径**: `DELETE /stars/{star_id}/fans/me`
- **功能**: 取消待审核申请 或 退出已批准的粉丝身份

---

## 数据模型

### 新增模型

| 模型 | 说明 | 主要字段 |
|------|------|----------|
| StarFan | 明星粉丝（申请-审核制） | star_id, user_id, status, apply_message, reviewed_by, reviewed_at |

### 状态定义

| 状态 | 说明 |
|------|------|
| `pending` | 待审核 |
| `approved` | 已通过（正式粉丝） |
| `rejected` | 已拒绝（可重新申请） |

### 索引优化

| 索引 | 说明 |
|------|------|
| `uq_star_fan` | 明星ID+用户ID 唯一约束 |
| `ix_starfan_star_status` | 明星ID+状态+时间（快速查询粉丝列表） |
| `ix_starfan_user` | 用户ID+状态（快速查询我的申请） |

---

## 文件变更

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/models.py` | 新增 StarFan 模型，Star 添加 fans 关系，User 添加 fan_applications 关系 |
| `app/schemas.py` | 新增粉丝申请/审核相关 Schema（5 个） |
| `app/routers/star_router.py` | 新增粉丝申请-审核路由（6 个接口） |
| `app/main.py` | 更新版本号至 1.0.48 |

---

## 数据库迁移

```bash
alembic revision --autogenerate -m "add_star_fan_table"
alembic upgrade head
```

**新增表**:
- `star_fans` - 明星粉丝表（申请-审核制）

**保留表**:
- `star_follows` - 关注表（无需审核）

---

## API 统计

| 模块 | 原接口数 | 新接口数 | 总计 |
|------|----------|----------|------|
| 明星模块 | 17 | 6 | 23 |
| **项目总计** | 84 | 6 | **90** |

---

## 使用示例

### 申请成为粉丝
```bash
curl -X POST "http://localhost:8000/stars/1/fans/apply" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"apply_message": "我是忠实粉丝，请批准"}'
```

### 管理员查看待审核
```bash
curl "http://localhost:8000/stars/1/fans/pending" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### 管理员审核
```bash
curl -X POST "http://localhost:8000/stars/1/fans/1/review" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "approved"}'
```

### 查看已通过的粉丝
```bash
curl "http://localhost:8000/stars/1/fans"
```

### 查看我的申请
```bash
curl "http://localhost:8000/stars/users/me/fan-applications" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 取消粉丝身份
```bash
curl -X DELETE "http://localhost:8000/stars/1/fans/me" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 验证清单

- [x] StarFan 数据模型（申请-审核制）
- [x] 状态字段：pending/approved/rejected
- [x] 申请留言字段
- [x] 审核人/审核时间字段
- [x] 唯一约束（防止重复申请）
- [x] 复合索引优化
- [x] 提交粉丝申请接口
- [x] 待审核列表接口
- [x] 审核申请接口
- [x] 已通过粉丝列表接口
- [x] 我的申请列表接口
- [x] 取消粉丝身份接口
- [x] 保留原有的关注功能（StarFollow）
- [x] 更新版本号

---

## 破坏性变更说明

⚠️ **此版本对粉丝功能进行了重构**：

1. **V1.0.47 的粉丝功能**已被替换为**申请-审核制**
2. **关注功能**（StarFollow）保持不变，无需审核
3. **粉丝功能**（StarFan）需要申请并审核

**数据迁移建议**：
- 如需将 V1.0.47 的粉丝数据迁移到新表，可执行：
```sql
-- 将原有关注数据转为粉丝申请（假设全部通过）
INSERT INTO star_fans (star_id, user_id, status, created_at)
SELECT star_id, user_id, 'approved', created_at FROM star_follows;
```

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
