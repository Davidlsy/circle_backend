# 更新日志 v1.0.62

## 版本信息
- **版本号**: v1.0.62
- **发布日期**: 2026-05-16
- **更新类型**: 功能新增

## 更新概述

本次更新在用户信息中新增**政治面貌**字段，支持三种政治面貌选项。

---

## 政治面貌选项

| 值 | 说明 |
|------|------|
| `masses` | 群众（默认） |
| `league` | 共青团员 |
| `party` | 中共党员 |

---

## 变更内容

### 1. 数据模型变更

User 表新增字段：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `political_status` | VARCHAR(20) | `masses` | 政治面貌 |

### 2. Schema 变更

- **UserUpdate**: 新增 `political_status` 可选字段（正则验证）
- **UserPublic**: 新增 `political_status` 字段（默认 `masses`）
- **新增常量**: `POLITICAL_STATUS_OPTIONS` 政治面貌映射

### 3. 接口变更

编辑个人资料接口 `PATCH /users/me` 新增 `political_status` 参数：

```json
{
  "nickname": "昵称",
  "bio": "个人简介",
  "political_status": "party"
}
```

所有返回用户信息的接口均包含 `political_status` 字段。

---

## 文件变更

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/models.py` | User 模型新增 political_status 字段 |
| `app/schemas.py` | UserUpdate/UserPublic 新增字段；新增 POLITICAL_STATUS_OPTIONS 常量 |
| `app/main.py` | 更新版本号至 1.0.62 |
| `FEATURES.md` | 更新用户模块说明，新增政治面貌选项表 |

---

## 数据库迁移

```bash
alembic revision --autogenerate -m "add_political_status_to_users"
alembic upgrade head
```

**变更内容**：
- users 表新增 `political_status` 字段（VARCHAR(20)，默认 `masses`）

---

## 使用示例

### 设置政治面貌
```bash
curl -X PATCH "http://localhost:8000/users/me" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"political_status": "party"}'
```

### 查看用户信息（含政治面貌）
```json
{
  "id": 1,
  "username": "user1",
  "nickname": "昵称",
  "bio": "个人简介",
  "political_status": "party",
  "is_superuser": false,
  "created_at": "2026-05-16T10:00:00"
}
```

---

## 验证清单

- [x] User 模型新增 political_status 字段
- [x] 默认值为 masses（群众）
- [x] UserUpdate 支持修改政治面貌（正则验证）
- [x] UserPublic 返回政治面貌
- [x] 新增 POLITICAL_STATUS_OPTIONS 常量
- [x] 更新 FEATURES.md
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
