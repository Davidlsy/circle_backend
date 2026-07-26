# 更新日志 v1.0.59

## 版本信息
- **版本号**: v1.0.59
- **发布日期**: 2026-05-15
- **更新类型**: 功能新增

## 更新概述

本次更新新增**粉丝牌/粉丝称号系统**。粉丝可以在个人主页展示至多一个明星的粉丝牌，根据粉丝的等级（路人粉/真爱粉/死忠粉）对应不同的粉丝牌名称和颜色。

---

## 粉丝牌系统

### 粉丝牌配置

| 粉丝类型 | 称号 | 粉丝牌名称模板 | 颜色 |
|----------|------|----------------|------|
| 路人粉 (casual) | 路人粉 | {明星名}的路人粉 | #808080 (灰色) |
| 真爱粉 (true_fan) | 真爱粉 | {明星名}的真爱粉 | #FF69B4 (粉色) |
| 死忠粉 (diehard) | 死忠粉 | {明星名}的死忠粉 | #FFD700 (金色) |

### 规则说明

- 每人**最多展示一个**粉丝牌在个人主页
- 粉丝牌在粉丝审核通过时**自动创建**
- 粉丝类型升级时，粉丝牌**自动更新**
- 用户可**自由选择**展示哪一个粉丝牌

---

## 新增接口

### 1. 我的粉丝牌

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 我的粉丝牌列表 | GET | `/fan-badges/my` | 获取我的所有粉丝牌 | 登录 |
| 当前展示的粉丝牌 | GET | `/fan-badges/my/displayed` | 获取我正在展示的粉丝牌 | 登录 |
| 设置展示的粉丝牌 | POST | `/fan-badges/my/display` | 设置要展示的粉丝牌 | 登录 |
| 取消展示粉丝牌 | DELETE | `/fan-badges/my/display` | 取消展示粉丝牌 | 登录 |

#### 1.1 设置展示的粉丝牌

- 每人最多展示一个粉丝牌
- 设置新的会**自动取消**之前的展示

```bash
curl -X POST "http://localhost:8000/fan-badges/my/display" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"badge_id": 1}'
```

---

### 2. 查看他人粉丝牌

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 查看用户展示的粉丝牌 | GET | `/fan-badges/user/{user_id}` | 查看用户展示的粉丝牌 | 公开 |
| 查看用户的所有粉丝牌 | GET | `/fan-badges/user/{user_id}/all` | 查看用户的所有粉丝牌 | 公开 |

---

### 3. 粉丝牌配置

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 获取粉丝牌配置 | GET | `/fan-badges/config` | 获取称号、颜色对应关系 | 公开 |

---

## 数据模型

### 新增模型

| 模型 | 说明 | 主要字段 |
|------|------|----------|
| FanBadge | 粉丝牌 | user_id, star_id, fan_type, badge_name, badge_level, badge_color, is_displayed |

### 字段说明

| 字段 | 说明 |
|------|------|
| `badge_name` | 粉丝牌名称，如 "张三的死忠粉" |
| `badge_level` | 粉丝牌等级（1=路人粉，2=真爱粉，3=死忠粉） |
| `badge_color` | 粉丝牌颜色（十六进制） |
| `is_displayed` | 是否在个人主页展示 |

### 关系变更

| 模型 | 新增关系 |
|------|----------|
| User | fan_badges (1对多) |
| Star | fan_badges (1对多) |

---

## 自动创建粉丝牌

粉丝审核通过时，系统自动创建对应的粉丝牌：

```python
# 审核通过
if data.status == "approved":
    fan.fan_type = data.fan_type
    # 自动创建/更新粉丝牌
    _get_or_create_badge(fan.user_id, star_id, data.fan_type, db)
```

---

## 文件变更

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `app/routers/fan_badge_router.py` | 粉丝牌路由（9 个接口） |

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/models.py` | 新增 FanBadge 模型；User/Star 添加 fan_badges 关系 |
| `app/schemas.py` | 新增粉丝牌相关 Schema（5 个）+ BADGE_CONFIG 配置 |
| `app/routers/star_router.py` | 粉丝审核通过时自动创建/更新粉丝牌 |
| `app/main.py` | 注册粉丝牌路由，更新版本号至 1.0.59 |

---

## 数据库迁移

```bash
alembic revision --autogenerate -m "add_fan_badge_table"
alembic upgrade head
```

**新增表**:
- `fan_badges` - 粉丝牌表

---

## API 统计

| 模块 | 原接口数 | 新接口数 | 总计 |
|------|----------|----------|------|
| 粉丝牌模块 | 0 | 9 | 9 |
| **项目总计** | 125 | 9 | **134** |

---

## 使用示例

### 查看我的粉丝牌
```bash
curl "http://localhost:8000/fan-badges/my" \
  -H "Authorization: Bearer TOKEN"
```

### 设置展示的粉丝牌
```bash
curl -X POST "http://localhost:8000/fan-badges/my/display" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"badge_id": 1}'
```

### 查看他人展示的粉丝牌
```bash
curl "http://localhost:8000/fan-badges/user/2"
```

### 获取粉丝牌配置
```bash
curl "http://localhost:8000/fan-badges/config"
```

---

## 验证清单

- [x] FanBadge 数据模型
- [x] 粉丝牌配置（路人粉/真爱粉/死忠粉对应不同称号和颜色）
- [x] 粉丝审核通过时自动创建粉丝牌
- [x] 粉丝类型升级时自动更新粉丝牌
- [x] 我的粉丝牌列表接口
- [x] 当前展示的粉丝牌接口
- [x] 设置展示的粉丝牌接口（每人最多一个）
- [x] 取消展示粉丝牌接口
- [x] 查看他人展示的粉丝牌接口（公开）
- [x] 粉丝牌配置接口（公开）
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
