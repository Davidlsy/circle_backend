# 更新日志 v1.0.66

## 版本信息
- **版本号**: v1.0.66
- **发布日期**: 2026-05-20
- **更新类型**: 安全修复 + 代码质量优化

## 更新概述

本次更新基于代码审计报告（CODE_AUDIT_REPORT.md），修复了 4 个安全问题、1 个性能问题、1 个代码重复问题和 1 个事务问题。

---

## 修复内容

### 🔴 SEC-001：密码重置功能 bug（严重）

**问题**：`ResetPasswordRequest` Schema 缺少 `email` 字段，导致密码重置功能完全不可用。

**修复**：
```python
# 修复前
class ResetPasswordRequest(BaseModel):
    code: str = Field(...)
    new_password: str = Field(...)

# 修复后
class ResetPasswordRequest(BaseModel):
    email: str = Field(..., description="用户邮箱")
    code: str = Field(...)
    new_password: str = Field(...)
```

**文件**：`app/schemas.py`

---

### 🔴 SEC-002：管理员身份信息泄露（严重）

**问题**：`UserPublic` Schema 包含 `is_superuser` 字段，公开接口可枚举管理员列表。

**修复**：从 `UserPublic` 中移除 `is_superuser` 字段，同步清理所有手动传递该字段的代码。

**影响文件**：
- `app/schemas.py` - UserPublic 移除 is_superuser
- `app/routers/follow_router.py` - 移除 6 处 is_superuser 赋值
- `app/routers/user_router.py` - 移除 1 处 is_superuser 赋值

---

### 🟠 SEC-003：用户名枚举漏洞（高危）

**问题**：`/forgot-password` 接口在不同情况下返回不同消息，可枚举有效用户名。

**修复**：统一所有情况下的返回消息，无论用户是否存在都返回相同响应。

```python
# 统一消息
msg = "如果账号存在且已绑定邮箱，验证码已发送"
```

**文件**：`app/routers/auth_router.py`

---

### 🟡 SEC-004：XSS 防护依赖可选库（中危）

**问题**：`bleach` 库为可选依赖，未安装时 HTML 内容不会被清理。

**修复**：当 `bleach` 不可用时，使用正则表达式移除危险标签（script/iframe/object/embed）和事件属性（on*）作为兜底防护。

**文件**：`app/utils/markdown_utils.py`

---

### ⚡ PERF-001 + DRY-001：公共工具函数

**问题**：粉丝验证逻辑在多个路由中重复；N+1 查询问题。

**修复**：创建公共工具函数 `app/utils/common.py`：
- `check_fan_permission()` - 统一粉丝权限验证
- `get_user_public_with_badge()` - 统一获取用户公开资料

**新增文件**：`app/utils/common.py`

---

### 🔧 TXN-001：数据库事务优化

**问题**：群聊创建使用 3 次 `db.commit()`，非原子操作。

**修复**：合并为 1 次 `db.commit()`，使用 `db.flush()` 替代中间提交。

**文件**：`app/routers/group_router.py`

---

## 文件变更

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `app/utils/common.py` | 公共工具函数（粉丝验证、用户资料获取） |

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/schemas.py` | SEC-001: ResetPasswordRequest 新增 email 字段；SEC-002: UserPublic 移除 is_superuser |
| `app/routers/auth_router.py` | SEC-003: 统一密码找回响应消息 |
| `app/routers/follow_router.py` | SEC-002: 移除 6 处 is_superuser 赋值 |
| `app/routers/user_router.py` | SEC-002: 移除 1 处 is_superuser 赋值 |
| `app/utils/markdown_utils.py` | SEC-004: bleach 不可用时正则兜底清理 |
| `app/routers/group_router.py` | TXN-001: 合并多次 commit |
| `app/main.py` | 更新版本号至 1.0.66 |
| `FEATURES.md` | 更新版本号和版本历史 |

---

## 安全问题修复汇总

| 问题编号 | 严重程度 | 状态 |
|----------|----------|------|
| SEC-001 密码重置 bug | 🔴 严重 | ✅ 已修复 |
| SEC-002 管理员身份泄露 | 🔴 严重 | ✅ 已修复 |
| SEC-003 用户名枚举漏洞 | 🟠 高危 | ✅ 已修复 |
| SEC-004 XSS 防护增强 | 🟡 中危 | ✅ 已修复 |

## 代码质量优化汇总

| 问题编号 | 状态 |
|----------|------|
| PERF-001 N+1 查询 | ✅ 已优化 |
| DRY-001 代码重复 | ✅ 已提取公共函数 |
| TXN-001 事务优化 | ✅ 已合并 commit |

---

## API 统计

| 项目 | 数量 |
|------|------|
| 功能模块 | 17 |
| API 接口 | 158 |
| 数据模型 | 29 |

---

## 验证清单

- [x] SEC-001: 密码重置 Schema 新增 email 字段
- [x] SEC-002: UserPublic 移除 is_superuser
- [x] SEC-002: follow_router.py 清理 is_superuser
- [x] SEC-002: user_router.py 清理 is_superuser
- [x] SEC-003: 统一密码找回响应消息
- [x] SEC-004: bleach 不可用时正则兜底清理
- [x] PERF-001: 创建公共工具函数
- [x] DRY-001: 提取粉丝验证为公共函数
- [x] TXN-001: 群聊创建合并 commit
- [x] 更新 FEATURES.md
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
