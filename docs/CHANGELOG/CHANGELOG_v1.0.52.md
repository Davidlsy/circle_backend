# 更新日志 v1.0.52

## 版本信息
- **版本号**: v1.0.52
- **发布日期**: 2026-05-14
- **更新类型**: 功能新增

## 更新概述

本次更新定义了**粉丝类型**，将粉丝分为三个等级：路人粉、真爱粉、死忠粉。管理员审核粉丝申请时可指定类型，也可后续升级粉丝类型。

---

## 粉丝类型定义

| 类型 | fan_type 值 | 说明 |
|------|------------|------|
| **路人粉** | `casual` | 普通粉丝，默认类型 |
| **真爱粉** | `true_fan` | 活跃粉丝，参与度高 |
| **死忠粉** | `diehard` | 核心粉丝，忠诚度最高 |

---

## 新增功能

### 1. 审核时指定粉丝类型

审核粉丝申请时新增 `fan_type` 字段：

```json
{
  "status": "approved",
  "fan_type": "true_fan",
  "review_message": "欢迎加入！"
}
```

### 2. 修改粉丝类型

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 修改粉丝类型 | PATCH | `/stars/{id}/fans/{fan_id}/type` | 升级/修改粉丝类型 | 管理员 |

#### 2.1 接口详情

- **路径**: `PATCH /stars/{star_id}/fans/{fan_id}/type?fan_type=true_fan`
- **fan_type 可选值**: `casual` / `true_fan` / `diehard`

```bash
# 升级为死忠粉
curl -X PATCH "http://localhost:8000/stars/1/fans/5/type?fan_type=diehard" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

---

## API 返回变更

### 粉丝信息新增 fan_type 字段

```json
{
  "id": 1,
  "star_id": 1,
  "user_id": 2,
  "status": "approved",
  "fan_type": "true_fan",
  "created_at": "2026-05-14T10:00:00",
  "user": {...}
}
```

### 我的申请新增 fan_type 字段

```json
{
  "id": 1,
  "star_id": 1,
  "status": "approved",
  "fan_type": "casual",
  "star": {...}
}
```

---

## 文件变更

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/models.py` | StarFan 新增 fan_type 字段 |
| `app/schemas.py` | StarFanPublic/MyFanApplicationPublic 新增 fan_type；StarFanReviewRequest 新增 fan_type |
| `app/routers/star_router.py` | 审核时设置 fan_type；新增修改粉丝类型接口 |
| `app/main.py` | 更新版本号至 1.0.52 |

---

## 数据库迁移

```bash
alembic revision --autogenerate -m "add_fan_type_to_star_fans"
alembic upgrade head
```

**变更内容**：
- star_fans 表新增 `fan_type` 字段（VARCHAR(20)，默认 `casual`）

---

## API 统计

| 模块 | 原接口数 | 新接口数 | 总计 |
|------|----------|----------|------|
| 明星模块 | 23 | 1 | 24 |
| **项目总计** | 105 | 1 | **106** |

---

## 使用示例

### 审核时指定粉丝类型
```bash
curl -X POST "http://localhost:8000/stars/1/fans/1/review" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "approved", "fan_type": "diehard"}'
```

### 升级粉丝类型
```bash
curl -X PATCH "http://localhost:8000/stars/1/fans/5/type?fan_type=true_fan" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

---

## 验证清单

- [x] StarFan 模型新增 fan_type 字段
- [x] 默认值为 casual（路人粉）
- [x] StarFanPublic 返回 fan_type
- [x] MyFanApplicationPublic 返回 fan_type
- [x] 审核时支持指定 fan_type
- [x] 新增修改粉丝类型接口
- [x] fan_type 正则验证
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
