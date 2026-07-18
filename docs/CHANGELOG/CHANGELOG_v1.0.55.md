# 更新日志 v1.0.55

## 版本信息
- **版本号**: v1.0.55
- **发布日期**: 2026-05-15
- **更新类型**: 功能新增

## 更新概述

本次更新新增**帖子置顶**和**帖子加精**功能。管理员可以对帖子进行置顶/取消置顶、加精/取消加精操作。帖子列表中置顶帖优先显示，加精帖有独立的列表入口。

---

## 新增功能

### 1. 帖子置顶

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 置顶/取消 | POST | `/posts/{id}/pin` | 切换帖子置顶状态 | 管理员 |

#### 1.1 功能说明

- 置顶帖子在帖子列表中**优先显示**
- 同样适用于通用帖子列表和明星板块帖子列表
- 再次调用同一接口可**取消置顶**

#### 1.2 使用示例

```bash
# 置顶帖子
curl -X POST "http://localhost:8000/posts/123/pin" \
  -H "Authorization: Bearer ADMIN_TOKEN"
# 返回: {"msg": "已置顶"}

# 取消置顶
curl -X POST "http://localhost:8000/posts/123/pin" \
  -H "Authorization: Bearer ADMIN_TOKEN"
# 返回: {"msg": "已取消置顶"}
```

---

### 2. 帖子加精

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 加精/取消 | POST | `/posts/{id}/feature` | 切换帖子加精状态 | 管理员 |
| 加精列表 | GET | `/posts/featured` | 获取所有加精帖子 | 公开 |

#### 2.1 功能说明

- 加精帖子标记为优质内容
- 有独立的**加精帖子列表**入口
- 帖子详情中显示加精状态
- 再次调用同一接口可**取消加精**

#### 2.2 使用示例

```bash
# 加精帖子
curl -X POST "http://localhost:8000/posts/123/feature" \
  -H "Authorization: Bearer ADMIN_TOKEN"
# 返回: {"msg": "已加精"}

# 查看加精帖子列表
curl "http://localhost:8000/posts/featured?page=1&page_size=20"
```

---

### 3. 帖子列表排序优化

**排序规则**（通用列表 + 明星板块列表）：

```
置顶帖（is_pinned=true）→ 按创建时间倒序
普通帖（is_pinned=false）→ 按创建时间倒序
```

置顶帖始终显示在列表最前面。

---

## 数据模型变更

### Post 表新增字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `is_pinned` | Boolean | False | 是否置顶 |
| `is_featured` | Boolean | False | 是否加精 |

### 帖子返回数据变更

所有帖子接口返回数据新增两个字段：

```json
{
  "id": 123,
  "title": "帖子标题",
  "is_pinned": false,
  "is_featured": true,
  ...
}
```

---

## 文件变更

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/models.py` | Post 模型新增 is_pinned、is_featured 字段 |
| `app/schemas.py` | PostPublic 新增 is_pinned、is_featured 字段 |
| `app/routers/post_router.py` | 新增置顶/加精/加精列表接口；列表排序优化 |
| `app/routers/star_router.py` | 明星板块帖子列表排序优化（置顶优先） |
| `app/main.py` | 更新版本号至 1.0.55 |

---

## 数据库迁移

```bash
alembic revision --autogenerate -m "add_post_pinned_featured"
alembic upgrade head
```

**变更内容**：
- posts 表新增 `is_pinned` 字段（Boolean，默认 False）
- posts 表新增 `is_featured` 字段（Boolean，默认 False）

---

## API 统计

| 模块 | 原接口数 | 新接口数 | 总计 |
|------|----------|----------|------|
| 帖子模块 | 11 | 3 | 14 |
| **项目总计** | 111 | 3 | **114** |

---

## 使用示例

### 管理员操作
```bash
# 置顶帖子
curl -X POST "http://localhost:8000/posts/123/pin" \
  -H "Authorization: Bearer ADMIN_TOKEN"

# 加精帖子
curl -X POST "http://localhost:8000/posts/456/feature" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### 用户查看
```bash
# 帖子列表（置顶帖优先显示）
curl "http://localhost:8000/posts/"

# 加精帖子列表
curl "http://localhost:8000/posts/featured"

# 明星板块帖子（置顶帖优先显示）
curl "http://localhost:8000/stars/1/posts"
```

---

## 验证清单

- [x] Post 模型新增 is_pinned、is_featured 字段
- [x] PostPublic Schema 新增对应字段
- [x] 置顶/取消置顶接口
- [x] 加精/取消加精接口
- [x] 加精帖子列表接口
- [x] 通用帖子列表排序优化（置顶优先）
- [x] 明星板块帖子列表排序优化（置顶优先）
- [x] 仅管理员可操作置顶/加精
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
