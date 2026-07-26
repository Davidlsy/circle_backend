# 更新日志 v1.0.65

## 版本信息
- **版本号**: v1.0.65
- **发布日期**: 2026-05-16
- **更新类型**: 功能新增

## 更新概述

本次更新在聊天（私信+群聊）中新增**定位功能**，用户可以发送当前位置信息（经纬度、位置名称、详细地址）。

---

## 功能说明

### 位置消息

用户可以在私信和群聊中发送位置消息，包含以下信息：

| 字段 | 类型 | 说明 |
|------|------|------|
| `latitude` | Float | 纬度（-90 ~ 90） |
| `longitude` | Float | 经度（-180 ~ 180） |
| `name` | String | 位置名称（如：北京市朝阳区） |
| `address` | String | 详细地址 |
| `poi_id` | String | 第三方POI ID（如高德地图POI ID） |

### 消息类型

聊天消息类型新增 `location`：

| 类型 | 说明 |
|------|------|
| `text` | 文本消息 |
| `image` | 图片消息 |
| `sticker` | 表情包消息 |
| `location` | 位置消息（新增） |
| `system` | 系统消息 |

---

## 变更内容

### 1. 数据模型变更

#### 新增 Location 模型

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer | 主键 |
| `latitude` | Float | 纬度 |
| `longitude` | Float | 经度 |
| `name` | String(200) | 位置名称 |
| `address` | String(500) | 详细地址 |
| `poi_id` | String(100) | 第三方POI ID |

#### Message 模型更新

| 字段 | 类型 | 说明 |
|------|------|------|
| `message_type` | String(20) | 新增字段，支持 text/image/sticker/location |
| `location_id` | Integer | 关联 Location 表 |

#### GroupMessage 模型更新

| 字段 | 类型 | 说明 |
|------|------|------|
| `message_type` | String(20) | 扩展支持 sticker/location |
| `location_id` | Integer | 关联 Location 表 |

---

## 使用示例

### 发送位置消息（私信）

```bash
curl -X POST "http://localhost:8000/messages/conversations/1/messages" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "我在这里",
    "message_type": "location",
    "location": {
      "latitude": 39.9042,
      "longitude": 116.4074,
      "name": "北京市朝阳区",
      "address": "北京市朝阳区某某街道123号",
      "poi_id": "B000A8URXB"
    }
  }'
```

### 发送位置消息（群聊）

```bash
curl -X POST "http://localhost:8000/groups/1/messages" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "集合地点",
    "message_type": "location",
    "location": {
      "latitude": 31.2304,
      "longitude": 121.4737,
      "name": "上海市人民广场",
      "address": "上海市黄浦区人民大道200号"
    }
  }'
```

### 返回示例

```json
{
  "id": 123,
  "conversation_id": 1,
  "sender_id": 1,
  "content": "我在这里",
  "message_type": "location",
  "is_read": false,
  "location": {
    "id": 1,
    "latitude": 39.9042,
    "longitude": 116.4074,
    "name": "北京市朝阳区",
    "address": "北京市朝阳区某某街道123号",
    "poi_id": "B000A8URXB",
    "created_at": "2026-05-16T10:00:00"
  },
  "created_at": "2026-05-16T10:00:00",
  "sender": {...}
}
```

---

## 文件变更

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/models.py` | 新增 Location 模型；Message/GroupMessage 添加 message_type 和 location_id 字段 |
| `app/schemas.py` | 新增 LocationPublic/LocationCreate Schema；更新 MessageSend/MessagePublic/GroupMessageCreate/GroupMessagePublic |
| `app/routers/message_router.py` | 更新 send_message 支持 location 类型 |
| `app/routers/group_router.py` | 更新 send_message 支持 location 类型 |
| `app/main.py` | 更新版本号至 1.0.65 |
| `FEATURES.md` | 更新私信/群聊模块说明，新增消息类型表 |

---

## 数据库迁移

```bash
alembic revision --autogenerate -m "add_location_and_message_types"
alembic upgrade head
```

**新增表**:
- `locations` - 位置信息表

**修改表**:
- `messages` - 添加 message_type 和 location_id 字段
- `group_messages` - 添加 location_id 字段

---

## API 统计

| 模块 | 原接口数 | 新接口数 | 总计 |
|------|----------|----------|------|
| 私信模块 | 6 | 0 | 6 |
| 群聊模块 | 14 | 0 | 14 |
| **项目总计** | 158 | 0 | **158** |

> 注：本次更新为现有接口扩展功能，未新增独立接口。

---

## 验证清单

- [x] Location 数据模型
- [x] LocationPublic/LocationCreate Schema
- [x] Message 模型添加 message_type 和 location_id
- [x] GroupMessage 模型添加 location_id
- [x] 私信发送消息支持 location 类型
- [x] 群聊发送消息支持 location 类型
- [x] 位置信息包含经纬度、名称、地址、POI ID
- [x] 更新 FEATURES.md
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
