# 更新日志 v1.0.49

## 版本信息
- **版本号**: v1.0.49
- **发布日期**: 2026-05-14
- **更新类型**: 功能新增

## 更新概述

本次更新在粉丝模块内新增**风纪委员会**，负责审核该明星板块下发布的帖子。成为风纪委员需要先成为已通过的粉丝，然后申请并经过审核。

---

## 功能架构

```
粉丝模块
├── 关注（StarFollow）        → 无需审核，即时关注
├── 粉丝（StarFan）           → 申请-审核制
└── 风纪委员会（DisciplineCommittee）→ 申请-审核制，负责审核帖子
    ├── 成员（member）         → 可审核帖子
    └── 委员长（chairman）     → 可审核帖子 + 审核风纪委员申请
```

---

## 新增功能

### 1. 申请加入风纪委员会

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 申请加入 | POST | `/stars/{id}/committee/apply` | 申请成为风纪委员 | 已通过的粉丝 |

#### 1.1 前置条件

- ✅ 必须是该明星的**已通过粉丝**（StarFan status=approved）
- ✅ 未被拒绝或已过期可重新申请

#### 1.2 请求示例

```bash
curl -X POST "http://localhost:8000/stars/1/committee/apply" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"apply_message": "我有丰富社区管理经验，希望能加入风纪委员会"}'
```

---

### 2. 风纪委员会管理

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 待审核列表 | GET | `/stars/{id}/committee/pending` | 查看待审核申请 | 管理员/委员长 |
| 审核申请 | POST | `/stars/{id}/committee/{app_id}/review` | 通过/拒绝申请 | 管理员/委员长 |
| 成员列表 | GET | `/stars/{id}/committee` | 查看已通过成员 | 公开 |
| 我的申请 | GET | `/stars/users/me/committee-applications` | 查看我的申请 | 登录 |
| 辞去职务 | DELETE | `/stars/{id}/committee/me` | 辞去风纪委员 | 成员 |

#### 2.1 审核申请

```bash
curl -X POST "http://localhost:8000/stars/1/committee/1/review" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "approved", "role": "member"}'
```

**role 可选值**：
- `member`（普通成员）：可审核帖子
- `chairman`（委员长）：可审核帖子 + 审核风纪委员申请

---

### 3. 风纪委员审核帖子

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 待审核帖子 | GET | `/stars/{id}/committee/posts/pending` | 查看待审核帖子 | 风纪委员 |
| 审核帖子 | POST | `/stars/{id}/committee/posts/{post_id}/audit` | 通过/驳回帖子 | 风纪委员 |

#### 3.1 查看待审核帖子

```bash
curl "http://localhost:8000/stars/1/committee/posts/pending?page=1&page_size=20" \
  -H "Authorization: Bearer COMMITTEE_TOKEN"
```

#### 3.2 审核帖子

```bash
# 通过
curl -X POST "http://localhost:8000/stars/1/committee/posts/123/audit?action=approve" \
  -H "Authorization: Bearer COMMITTEE_TOKEN"

# 驳回
curl -X POST "http://localhost:8000/stars/1/committee/posts/123/audit?action=reject&reason=内容违规" \
  -H "Authorization: Bearer COMMITTEE_TOKEN"
```

---

## 数据模型

### 新增模型

| 模型 | 说明 | 主要字段 |
|------|------|----------|
| DisciplineCommittee | 风纪委员会 | star_id, user_id, status, role, apply_message, reviewed_by, reviewed_at |

### 状态定义

| 状态 | 说明 |
|------|------|
| `pending` | 待审核 |
| `approved` | 已通过（正式委员） |
| `rejected` | 已拒绝（可重新申请） |
| `resigned` | 已辞职（可重新申请） |

### 角色定义

| 角色 | 权限 |
|------|------|
| `member` | 审核该明星板块的帖子 |
| `chairman` | 审核帖子 + 审核风纪委员申请 |

### 索引优化

| 索引 | 说明 |
|------|------|
| `uq_discipline_committee` | 明星ID+用户ID 唯一约束 |
| `ix_dc_star_status` | 明星ID+状态+时间 |
| `ix_dc_user` | 用户ID+状态 |

---

## 权限体系

```
管理员 (is_superuser)
├── 审核所有明星的风纪委员申请
├── 审核所有帖子（原有 /admin 接口）
└── 管理所有明星

委员长 (chairman)
├── 审核该明星的风纪委员申请
└── 审核该明星板块的帖子

普通委员 (member)
└── 审核该明星板块的帖子

已通过粉丝
└── 可申请加入风纪委员会
```

---

## 文件变更

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `app/routers/discipline_router.py` | 风纪委员会路由（8 个接口） |

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/models.py` | 新增 DisciplineCommittee 模型，Star/User 添加关系 |
| `app/schemas.py` | 新增风纪委员会相关 Schema（5 个） |
| `app/main.py` | 注册风纪委员会路由，更新版本号至 1.0.49 |

---

## 数据库迁移

```bash
alembic revision --autogenerate -m "add_discipline_committee_table"
alembic upgrade head
```

**新增表**:
- `discipline_committees` - 风纪委员会表

---

## API 统计

| 模块 | 原接口数 | 新接口数 | 总计 |
|------|----------|----------|------|
| 风纪委员会 | 0 | 8 | 8 |
| **项目总计** | 90 | 8 | **98** |

---

## 使用流程

### 完整流程示例

```bash
# 1. 成为粉丝（需先通过审核）
curl -X POST "http://localhost:8000/stars/1/fans/apply" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"apply_message": "请批准"}'

# 2. 管理员审核粉丝
curl -X POST "http://localhost:8000/stars/1/fans/1/review" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{"status": "approved"}'

# 3. 申请加入风纪委员会
curl -X POST "http://localhost:8000/stars/1/committee/apply" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"apply_message": "我有管理经验"}'

# 4. 管理员审核风纪委员申请
curl -X POST "http://localhost:8000/stars/1/committee/1/review" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{"status": "approved", "role": "member"}'

# 5. 查看待审核帖子
curl "http://localhost:8000/stars/1/committee/posts/pending" \
  -H "Authorization: Bearer TOKEN"

# 6. 审核帖子
curl -X POST "http://localhost:8000/stars/1/committee/posts/123/audit?action=approve" \
  -H "Authorization: Bearer TOKEN"
```

---

## 验证清单

- [x] DisciplineCommittee 数据模型
- [x] 状态字段：pending/approved/rejected/resigned
- [x] 角色字段：member/chairman
- [x] 前置条件：必须是已通过的粉丝
- [x] 申请加入风纪委员会
- [x] 待审核申请列表
- [x] 审核申请（分配角色）
- [x] 成员列表（chairman 排前面）
- [x] 我的申请列表
- [x] 辞去职务
- [x] 风纪委员审核帖子（通过/驳回）
- [x] 待审核帖子列表
- [x] 权限控制（管理员/委员长/成员）
- [x] 唯一约束和复合索引
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
