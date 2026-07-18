# 更新日志 v1.0.63

## 版本信息
- **版本号**: v1.0.63
- **发布日期**: 2026-05-16
- **更新类型**: 功能新增

## 更新概述

本次更新新增**粉丝圈共同空间照片功能**。所有粉丝都可以上传照片到粉丝圈共同空间，照片需要经过管理员审核后才能公开显示。

---

## 功能说明

### 共同空间

每个粉丝圈都有一个共同空间，用于粉丝分享照片：
- 所有已通过的粉丝都可以上传照片
- 照片上传后进入待审核状态
- 管理员审核通过后，照片在共同空间公开显示
- 支持照片描述、驳回原因等

### 照片上传限制

| 限制项 | 说明 |
|--------|------|
| 支持格式 | jpeg / png / gif / webp |
| 单文件大小 | 最大 5MB |
| 上传权限 | 已通过的粉丝 |
| 显示条件 | 管理员审核通过 |

### 照片状态

| 状态 | 说明 |
|------|------|
| `pending` | 待审核（默认） |
| `approved` | 已通过（公开显示） |
| `rejected` | 已驳回 |

---

## 新增接口

| 接口 | 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|------|
| 上传照片 | POST | `/fan-circles/{circle_id}/photos` | 上传照片到共同空间 | 登录（粉丝） |
| 已审核照片列表 | GET | `/fan-circles/{circle_id}/photos` | 获取已审核通过的照片 | 公开 |
| 所有照片列表 | GET | `/fan-circles/{circle_id}/photos/all` | 获取所有照片（含待审核） | 登录（管理员） |
| 我上传的照片 | GET | `/fan-circles/{circle_id}/photos/my` | 获取我上传的照片 | 登录（粉丝） |
| 待审核照片 | GET | `/fan-circles/{circle_id}/photos/pending` | 获取待审核照片列表 | 登录（管理员） |
| 审核照片 | POST | `/fan-circles/{circle_id}/photos/{photo_id}/audit` | 审核照片（通过/驳回） | 登录（管理员） |
| 快捷通过 | POST | `/fan-circles/{circle_id}/photos/{photo_id}/approve` | 快捷通过照片 | 登录（管理员） |
| 快捷驳回 | POST | `/fan-circles/{circle_id}/photos/{photo_id}/reject` | 快捷驳回照片 | 登录（管理员） |
| 删除照片 | DELETE | `/fan-circles/{circle_id}/photos/{photo_id}` | 删除照片 | 登录（上传者/管理员） |

---

## 数据模型

### 新增模型

| 模型 | 表名 | 说明 |
|------|------|------|
| FanCirclePhoto | fan_circle_photos | 粉丝圈共同空间照片表 |

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `circle_id` | Integer | 粉丝圈ID |
| `user_id` | Integer | 上传者ID |
| `url` | String | 图片URL |
| `filename` | String | 原始文件名 |
| `description` | String | 照片描述 |
| `status` | String | 状态（pending/approved/rejected） |
| `reviewed_by` | Integer | 审核人ID |
| `reviewed_at` | DateTime | 审核时间 |
| `reject_reason` | String | 驳回原因 |

---

## 文件变更

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `app/routers/circle_photo_router.py` | 粉丝圈照片路由（9 个接口） |

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/models.py` | 新增 FanCirclePhoto 模型；FanCircle/User 添加关系 |
| `app/schemas.py` | 新增照片相关 Schema（4 个） |
| `app/main.py` | 注册照片路由，更新版本号至 1.0.63 |
| `FEATURES.md` | 新增粉丝圈共同空间模块说明 |

---

## 数据库迁移

```bash
alembic revision --autogenerate -m "add_fan_circle_photos_table"
alembic upgrade head
```

**新增表**:
- `fan_circle_photos` - 粉丝圈共同空间照片表

---

## API 统计

| 模块 | 原接口数 | 新接口数 | 总计 |
|------|----------|----------|------|
| 粉丝圈共同空间模块 | 0 | 9 | 9 |
| **项目总计** | 140 | 9 | **149** |

---

## 使用示例

### 上传照片
```bash
curl -X POST "http://localhost:8000/fan-circles/1/photos" \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@photo.jpg" \
  -F "description=演唱会现场照片"
```

### 查看已审核照片
```bash
curl "http://localhost:8000/fan-circles/1/photos?page=1&page_size=20"
```

### 审核照片
```bash
curl -X POST "http://localhost:8000/fan-circles/1/photos/1/audit" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "approved"}'
```

### 驳回照片
```bash
curl -X POST "http://localhost:8000/fan-circles/1/photos/1/reject?reject_reason=图片不清晰" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

---

## 验证清单

- [x] FanCirclePhoto 数据模型
- [x] 照片上传接口（粉丝权限）
- [x] 照片格式验证（jpeg/png/gif/webp）
- [x] 照片大小验证（5MB）
- [x] 已审核照片列表（公开）
- [x] 所有照片列表（管理员）
- [x] 我上传的照片（粉丝）
- [x] 待审核照片列表（管理员）
- [x] 照片审核接口（管理员）
- [x] 快捷通过/驳回接口
- [x] 照片删除接口（上传者/管理员）
- [x] 更新 FEATURES.md
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
