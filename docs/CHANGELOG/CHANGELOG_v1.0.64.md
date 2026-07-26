# 更新日志 v1.0.64

## 版本信息
- **版本号**: v1.0.64
- **发布日期**: 2026-05-16
- **更新类型**: 功能新增

## 更新概述

本次更新新增**表情包功能**。用户可以上传表情包、收藏表情包（上限100个），在群聊和私信中使用表情包发送消息。

---

## 功能说明

### 表情包上传

| 限制项 | 说明 |
|--------|------|
| 支持格式 | gif / webp / png |
| 单文件大小 | 最大 2MB |
| 分类 | default（默认）/ emoji（表情）/ custom（自定义） |
| 公开性 | 公开表情包所有用户可见 |

### 用户收藏

| 限制项 | 说明 |
|--------|------|
| 收藏上限 | 100 个 |
| 排序 | 支持自定义排序 |
| 去重 | 同一表情包不可重复收藏 |

### 聊天中使用

在群聊和私信中，消息类型新增 `sticker`，发送时携带 `sticker_id`：

```json
{
  "content": "",
  "message_type": "sticker",
  "sticker_id": 1
}
```

---

## 新增接口

### 表情包管理

| 接口 | 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|------|
| 上传表情包 | POST | `/stickers/` | 上传表情包 | 登录 |
| 表情包列表 | GET | `/stickers/` | 获取公开表情包列表 | 公开 |
| 搜索表情包 | GET | `/stickers/search` | 按名称搜索表情包 | 公开 |
| 分类列表 | GET | `/stickers/categories` | 获取表情包分类 | 公开 |
| 删除表情包 | DELETE | `/stickers/{sticker_id}` | 删除表情包 | 登录（上传者/管理员） |

### 用户收藏

| 接口 | 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|------|
| 我的收藏 | GET | `/stickers/my` | 获取我的表情包收藏 | 登录 |
| 收藏表情包 | POST | `/stickers/my/{sticker_id}` | 收藏表情包 | 登录 |
| 移除收藏 | DELETE | `/stickers/my/{sticker_id}` | 从收藏中移除 | 登录 |
| 收藏数量 | GET | `/stickers/my/count` | 获取收藏数量 | 登录 |

---

## 数据模型

### 新增模型

| 模型 | 表名 | 说明 |
|------|------|------|
| Sticker | stickers | 表情包表 |
| UserSticker | user_stickers | 用户表情包收藏表 |

### Sticker 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| name | String(100) | 表情包名称 |
| url | String(500) | 图片URL |
| filename | String(255) | 原始文件名 |
| category | String(50) | 分类（default/emoji/custom） |
| width | Integer | 图片宽度 |
| height | Integer | 图片高度 |
| uploader_id | Integer | 上传者ID |
| is_public | Boolean | 是否公开 |

### UserSticker 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | Integer | 用户ID |
| sticker_id | Integer | 表情包ID |
| sort_order | Integer | 排序 |

---

## 文件变更

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `app/routers/sticker_router.py` | 表情包路由（9 个接口） |

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/models.py` | 新增 Sticker、UserSticker 模型；User 添加 user_stickers 关系 |
| `app/schemas.py` | 新增表情包相关 Schema（5 个）+ MAX_USER_STICKERS 常量 |
| `app/main.py` | 注册表情包路由，更新版本号至 1.0.64 |
| `FEATURES.md` | 新增表情包模块说明 |

---

## 数据库迁移

```bash
alembic revision --autogenerate -m "add_sticker_tables"
alembic upgrade head
```

**新增表**:
- `stickers` - 表情包表
- `user_stickers` - 用户表情包收藏表

---

## API 统计

| 模块 | 原接口数 | 新接口数 | 总计 |
|------|----------|----------|------|
| 表情包模块 | 0 | 9 | 9 |
| **项目总计** | 149 | 9 | **158** |

---

## 使用示例

### 上传表情包
```bash
curl -X POST "http://localhost:8000/stickers/" \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@sticker.gif" \
  -F "name=开心" \
  -F "category=emoji"
```

### 获取表情包列表
```bash
curl "http://localhost:8000/stickers/?category=emoji&page_size=50"
```

### 搜索表情包
```bash
curl "http://localhost:8000/stickers/search?keyword=开心"
```

### 收藏表情包
```bash
curl -X POST "http://localhost:8000/stickers/my/1" \
  -H "Authorization: Bearer TOKEN"
```

### 查看我的收藏
```bash
curl "http://localhost:8000/stickers/my" \
  -H "Authorization: Bearer TOKEN"
```

### 在聊天中使用表情包
```bash
# 群聊发送表情包
curl -X POST "http://localhost:8000/groups/1/messages" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "", "message_type": "sticker", "sticker_id": 1}'
```

---

## 验证清单

- [x] Sticker 数据模型
- [x] UserSticker 数据模型（用户收藏）
- [x] 表情包上传接口（格式/大小验证）
- [x] 表情包列表接口（公开）
- [x] 表情包搜索接口
- [x] 表情包分类列表接口
- [x] 删除表情包接口
- [x] 我的收藏列表接口
- [x] 收藏表情包接口（上限100个）
- [x] 移除收藏接口
- [x] 收藏数量接口
- [x] 群聊/私信支持 sticker 消息类型
- [x] 更新 FEATURES.md
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
