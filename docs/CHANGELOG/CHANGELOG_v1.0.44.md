# 更新日志 v1.0.44

## 版本信息
- **版本号**: v1.0.44
- **发布日期**: 2026-05-14
- **更新类型**: 功能新增

## 更新概述

本次更新新增**群聊功能**，支持创建群聊、邀请成员、群内发消息、成员角色管理、退出/解散群聊等完整的群聊功能。

---

## 新增功能

### 1. 群聊管理

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 创建群聊 | POST | `/groups/` | 创建新群聊 | 登录 |
| 我的群列表 | GET | `/groups/` | 获取我加入的群聊 | 登录 |
| 群聊详情 | GET | `/groups/{id}` | 获取群聊信息 | 群成员 |
| 更新群信息 | PUT | `/groups/{id}` | 修改群名称/描述 | 群主/管理员 |
| 解散群聊 | DELETE | `/groups/{id}` | 解散群聊 | 群主 |

#### 1.1 创建群聊

- **路径**: `POST /groups/`
- **请求体**:
  ```json
  {
    "name": "群名称",
    "description": "群描述（可选）",
    "max_members": 200
  }
  ```
- **功能**: 创建者自动成为群主，自动发送系统消息

#### 1.2 成员角色

| 角色 | 权限 |
|------|------|
| `owner`（群主） | 所有权限：修改群信息、邀请/移除成员、设置角色、解散群聊 |
| `admin`（管理员） | 邀请/移除普通成员 |
| `member`（普通成员） | 发送消息、查看成员、退出群聊 |

---

### 2. 成员管理

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 成员列表 | GET | `/groups/{id}/members` | 获取群成员列表 | 群成员 |
| 邀请成员 | POST | `/groups/{id}/invite` | 批量邀请用户 | 群主/管理员 |
| 加入群聊 | POST | `/groups/{id}/join` | 申请加入群聊 | 登录 |
| 退出群聊 | POST | `/groups/{id}/leave` | 退出群聊 | 群成员 |
| 移除成员 | DELETE | `/groups/{id}/members/{uid}` | 踢出成员 | 群主/管理员 |
| 设置角色 | PATCH | `/groups/{id}/members/{uid}/role` | 设置管理员/普通成员 | 群主 |

#### 2.1 邀请成员

- **路径**: `POST /groups/{id}/invite`
- **请求体**:
  ```json
  {
    "user_ids": [1, 2, 3]
  }
  ```
- **限制**: 最多一次邀请 50 人，不能超过群最大成员数

#### 2.2 设置角色

- **路径**: `PATCH /groups/{id}/members/{uid}/role`
- **请求体**:
  ```json
  {
    "role": "admin"
  }
  ```
- **可选值**: `admin` / `member`

---

### 3. 群消息

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 消息列表 | GET | `/groups/{id}/messages` | 获取群聊消息（分页） | 群成员 |
| 发送消息 | POST | `/groups/{id}/messages` | 发送群消息 | 群成员 |

#### 3.1 发送消息

- **路径**: `POST /groups/{id}/messages`
- **请求体**:
  ```json
  {
    "content": "消息内容",
    "message_type": "text"
  }
  ```
- **message_type**: `text`（文本）/ `image`（图片）

#### 3.2 系统消息

以下操作会自动发送系统消息：
- 创建群聊
- 邀请成员
- 成员加入
- 成员退出
- 成员被移除

---

## 数据模型

### 新增模型

| 模型 | 说明 | 主要字段 |
|------|------|----------|
| GroupChat | 群聊 | id, name, description, avatar, owner_id, max_members |
| GroupMember | 群成员 | id, group_id, user_id, role, joined_at, muted |
| GroupMessage | 群消息 | id, group_id, sender_id, content, message_type |

### 索引优化

| 索引 | 说明 |
|------|------|
| `uq_group_member` | 群ID+用户ID 唯一约束（防止重复加入） |
| `ix_groupmember_user` | 用户ID+群ID 复合索引（快速查询用户所在群） |

---

## 文件变更

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `app/routers/group_router.py` | 群聊路由（14 个接口） |

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/models.py` | 新增 GroupChat、GroupMember、GroupMessage 模型 |
| `app/schemas.py` | 新增群聊相关 Schema（8 个） |
| `app/main.py` | 注册群聊路由，更新版本号至 1.0.44 |

---

## 数据库迁移

```bash
alembic revision --autogenerate -m "add_group_chat_tables"
alembic upgrade head
```

**新增表**:
- `group_chats`
- `group_members`
- `group_messages`

---

## API 统计

| 模块 | 原接口数 | 新接口数 | 总计 |
|------|----------|----------|------|
| 群聊模块 | 0 | 14 | 14 |
| **项目总计** | 53 | 14 | **67** |

---

## 使用示例

### 创建群聊
```bash
curl -X POST "http://localhost:8000/groups/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "粉丝交流群", "description": "讨论最新动态", "max_members": 100}'
```

### 邀请成员
```bash
curl -X POST "http://localhost:8000/groups/1/invite" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_ids": [2, 3, 4]}'
```

### 发送消息
```bash
curl -X POST "http://localhost:8000/groups/1/messages" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "大家好！", "message_type": "text"}'
```

### 获取消息列表
```bash
curl "http://localhost:8000/groups/1/messages?page=1&page_size=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 安全特性

| 特性 | 说明 |
|------|------|
| 权限控制 | 群主/管理员/成员三级权限 |
| 成员验证 | 所有操作验证群成员身份 |
| 唯一约束 | 防止重复加入群聊 |
| 成员上限 | 可配置最大成员数（默认 200，最大 500） |
| 群主保护 | 群主不能被移除，不能退出（需先解散） |
| 管理员保护 | 管理员只能被群主移除 |

---

## 验证清单

- [x] GroupChat 数据模型
- [x] GroupMember 数据模型（唯一约束+索引）
- [x] GroupMessage 数据模型
- [x] 创建群聊（自动设群主）
- [x] 获取我的群列表
- [x] 获取群详情
- [x] 更新群信息
- [x] 解散群聊
- [x] 成员列表
- [x] 邀请成员
- [x] 加入群聊
- [x] 退出群聊
- [x] 移除成员
- [x] 设置成员角色
- [x] 发送群消息
- [x] 获取消息列表
- [x] 系统消息
- [x] 权限控制
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
