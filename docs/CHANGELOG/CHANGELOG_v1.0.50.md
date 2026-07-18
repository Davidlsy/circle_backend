# 更新日志 v1.0.50

## 版本信息
- **版本号**: v1.0.50
- **发布日期**: 2026-05-14
- **更新类型**: 功能新增

## 更新概述

本次更新新增**用户举报帖子功能**，用户可举报违规帖子，管理员审核处理举报。举报成立时帖子会被自动驳回。

---

## 新增功能

### 1. 用户举报

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 举报原因列表 | GET | `/reports/reasons` | 获取举报原因分类 | 公开 |
| 提交举报 | POST | `/reports/` | 举报帖子 | 登录 |
| 我的举报 | GET | `/reports/my` | 查看我的举报记录 | 登录 |

#### 1.1 举报原因分类

| 原因 | 说明 |
|------|------|
| 垃圾广告 | 推广广告、营销内容 |
| 色情低俗 | 涉黄内容 |
| 虚假信息 | 谣言、不实信息 |
| 人身攻击 | 辱骂、恐吓、骚扰 |
| 侵犯版权 | 盗用他人作品 |
| 违法违规 | 违反法律法规 |
| 恶意刷屏 | 重复无意义内容 |
| 其他 | 其他违规情况 |

#### 1.2 提交举报

- **路径**: `POST /reports/`
- **请求体**:
  ```json
  {
    "post_id": 123,
    "reason": "色情低俗",
    "description": "该帖子包含不当内容，请处理"
  }
  ```
- **限制**: 同一用户对同一帖子只能有一个待处理的举报

#### 1.3 举报状态

| 状态 | 说明 |
|------|------|
| `pending` | 待处理 |
| `processing` | 处理中 |
| `resolved` | 举报成立（帖子自动驳回） |
| `dismissed` | 举报不成立 |

---

### 2. 管理员处理举报

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 举报列表 | GET | `/reports/` | 获取所有举报 | 管理员 |
| 举报统计 | GET | `/reports/stats` | 举报统计数据 | 管理员 |
| 举报详情 | GET | `/reports/{id}` | 获取举报详情 | 管理员/举报人 |
| 处理举报 | POST | `/reports/{id}/handle` | 处理举报 | 管理员 |

#### 2.1 举报列表

- **路径**: `GET /reports/`
- **查询参数**:
  - `status`: 按状态筛选（可选）
  - `post_id`: 按帖子筛选（可选）
  - `page` / `page_size`: 分页

#### 2.2 举报统计

- **路径**: `GET /reports/stats`
- **返回**:
  ```json
  {
    "pending": 10,
    "processing": 2,
    "resolved": 50,
    "dismissed": 20,
    "total": 82
  }
  ```

#### 2.3 处理举报

- **路径**: `POST /reports/{id}/handle`
- **请求体**:
  ```json
  {
    "status": "resolved",
    "handle_result": "经核实，该帖子确实违规，已驳回"
  }
  ```
- **status 可选值**:
  - `resolved`（成立）：帖子自动被驳回
  - `dismissed`（不成立）：帖子不受影响

---

## 数据模型

### 新增模型

| 模型 | 说明 | 主要字段 |
|------|------|----------|
| Report | 举报 | reporter_id, post_id, reason, description, status, handled_by, handle_result |

### 索引优化

| 索引 | 说明 |
|------|------|
| `ix_report_post_status` | 帖子ID+状态（快速查询帖子举报） |
| `ix_report_reporter` | 举报人ID+时间（快速查询我的举报） |
| `ix_report_status` | 状态+时间（快速查询待处理举报） |

---

## 文件变更

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `app/routers/report_router.py` | 举报路由（7 个接口） |

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/models.py` | 新增 Report 模型，User 添加 reports_made，Post 添加 reports |
| `app/schemas.py` | 新增举报相关 Schema（6 个）+ REPORT_REASONS 常量 |
| `app/main.py` | 注册举报路由，更新版本号至 1.0.50 |

---

## 数据库迁移

```bash
alembic revision --autogenerate -m "add_report_table"
alembic upgrade head
```

**新增表**:
- `reports` - 举报表

---

## API 统计

| 模块 | 原接口数 | 新接口数 | 总计 |
|------|----------|----------|------|
| 举报模块 | 0 | 7 | 7 |
| **项目总计** | 98 | 7 | **105** |

---

## 使用示例

### 获取举报原因
```bash
curl "http://localhost:8000/reports/reasons"
```

### 举报帖子
```bash
curl -X POST "http://localhost:8000/reports/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"post_id": 123, "reason": "色情低俗", "description": "内容违规"}'
```

### 查看我的举报
```bash
curl "http://localhost:8000/reports/my" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 管理员查看举报列表
```bash
curl "http://localhost:8000/reports/?status=pending" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### 管理员处理举报
```bash
curl -X POST "http://localhost:8000/reports/1/handle" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "resolved", "handle_result": "已核实违规"}'
```

---

## 验证清单

- [x] Report 数据模型
- [x] 举报原因分类常量
- [x] 提交举报接口（防重复举报）
- [x] 举报原因验证
- [x] 我的举报列表
- [x] 管理员举报列表（支持筛选）
- [x] 举报统计数据
- [x] 举报详情
- [x] 处理举报（成立/不成立）
- [x] 举报成立时自动驳回帖子
- [x] 复合索引优化
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
