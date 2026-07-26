# 粉丝社群平台代码审计报告

> **审计日期**: 2026-05-20
> **审计版本**: v1.0.65
> **审计范围**: 项目全部代码
> **审计方法**: 静态代码分析 + 安全模式审查

---

## 一、审计概述

### 1.1 项目信息

| 项目 | 信息 |
|------|------|
| 项目名称 | 粉丝社群平台后端 API |
| 技术栈 | FastAPI + SQLAlchemy + SQLite/PostgreSQL |
| 代码规模 | ~160 个 API 接口，27 个数据模型 |
| 代码位置 | `/workspace/fan_community_backend/` |

### 1.2 审计范围

| 审计类别 | 涉及文件 |
|----------|----------|
| 认证模块 | `app/auth.py`, `app/routers/auth_router.py` |
| 数据验证 | `app/schemas.py` |
| 路由接口 | `app/routers/` 目录下所有路由文件 |
| 数据模型 | `app/models.py` |
| 工具函数 | `app/utils/markdown_utils.py` |
| 配置文件 | `app/config.py` |

---

## 二、安全问题（按严重程度）

### 2.1 【严重】密码重置功能无法使用

| 项目 | 内容 |
|------|------|
| **问题编号** | SEC-001 |
| **严重程度** | 🔴 严重 |
| **影响范围** | 所有用户 |

**问题描述**:
`ResetPasswordRequest` Schema 缺少 `email` 字段，导致密码重置功能完全无法正常工作。

**代码位置**:
```python
# app/schemas.py 第664-667行
class ResetPasswordRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6, max_length=128)
    # 缺少 email 字段！

# app/routers/auth_router.py 第211行
latest_code = db.query(VerificationCode).filter(
    VerificationCode.email == request.email,  # request.email 不存在！
    ...
)
```

**修复建议**:
```python
class ResetPasswordRequest(BaseModel):
    email: str = Field(..., description="用户邮箱")
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6, max_length=128)
```

---

### 2.2 【严重】管理员身份信息泄露

| 项目 | 内容 |
|------|------|
| **问题编号** | SEC-002 |
| **严重程度** | 🔴 严重 |
| **影响范围** | 所有用户公开资料接口 |

**问题描述**:
`UserPublic` Schema 包含 `is_superuser` 字段，攻击者可枚举系统管理员列表。

**代码位置**:
```python
# app/schemas.py 第34-45行
class UserPublic(BaseModel):
    id: int
    username: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    political_status: Optional[str] = "masses"
    is_superuser: bool  # 不应在公开接口返回！
    created_at: datetime
```

**修复建议**:
1. 创建 `UserPublicWithoutAdmin` 不含 `is_superuser`
2. 公开接口使用简化 Schema

---

### 2.3 【高危】用户名枚举漏洞

| 项目 | 内容 |
|------|------|
| **问题编号** | SEC-003 |
| **严重程度** | 🟠 高危 |
| **影响范围** | `/forgot-password` 接口 |

**问题描述**:
密码找回接口对用户存在与否返回不同响应，可枚举有效用户名。

**代码位置**:
```python
# app/routers/auth_router.py 第131-141行
if not user:
    return ForgotPasswordResponse(msg="如果账号存在，验证码已发送", code="", ...)
# 用户存在时返回不同消息
```

**修复建议**: 无论用户是否存在，都返回完全相同的响应。

---

### 2.4 【中危】XSS 防护依赖可选库

| 项目 | 内容 |
|------|------|
| **问题编号** | SEC-004 |
| **严重程度** | 🟡 中危 |

**问题描述**:
XSS 防护依赖 `bleach` 库，如果未安装则 Markdown/HTML 内容不会被清理。

**代码位置**:
```python
# app/utils/markdown_utils.py 第13-26行
try:
    import bleach
    BLEACH_AVAILABLE = True
except ImportError:
    BLEACH_AVAILABLE = False  # 库不存在时无防护！
```

---

### 2.5 【低危】验证码暴力破解风险

| 项目 | 内容 |
|------|------|
| **问题编号** | SEC-005 |
| **严重程度** | 🟢 低危 |

**问题描述**:
验证码仅有尝试次数限制（5次），缺少时间窗口限制。

---

## 三、代码质量问题（按严重程度）

### 3.1 【高】N+1 查询问题

| 问题编号 | 问题描述 | 涉及文件 |
|----------|----------|----------|
| PERF-001 | 热门推荐计算对每个帖子执行 3 次单独查询 | `post_router.py` |
| PERF-002 | 粉丝列表循环内查询用户 | `follow_router.py` |
| PERF-003 | 明星粉丝列表 N+1 问题 | `star_router.py` |

**示例代码**:
```python
# post_router.py 第1170-1188行
def _calc_heat_score(post: Post, db: Session) -> float:
    like_count = db.query(func.count(Like.id))...  # 每个帖子单独查询
    comment_count = db.query(func.count(Comment.id))...  # 每个帖子单独查询
    collect_count = db.query(func.count(Collection.id))...  # 每个帖子单独查询
```

**修复建议**: 使用 JOIN 或预加载批量查询。

---

### 3.2 【高】数据库事务问题

| 问题编号 | 问题描述 | 涉及文件 |
|----------|----------|----------|
| TXN-001 | 热门推荐接口无分页限制，可能加载全表 | `post_router.py` |
| TXN-002 | 群聊创建多次 commit，非原子操作 | `group_router.py` |

**示例代码**:
```python
# group_router.py 第39-81行
db.commit()  # 第1次
db.commit()  # 第2次
db.commit()  # 第3次
```

---

### 3.3 【中】重复代码

| 问题编号 | 问题描述 | 涉及文件 |
|----------|----------|----------|
| DRY-001 | 粉丝验证逻辑在多个路由重复 | `star_router.py`, `post_router.py`, `checkin_router.py` |
| DRY-002 | 分页查询逻辑重复 | 所有路由文件 |
| DRY-003 | 用户查询逻辑重复 | `user_router.py`, `follow_router.py` |

---

### 3.4 【中】文件上传异常处理

| 问题编号 | 问题描述 | 涉及文件 |
|----------|----------|----------|
| FILE-001 | 上传中途失败，已保存文件不会被清理 | `post_router.py`, `circle_photo_router.py` |

---

## 四、安全实践评估

| 安全方面 | 评估 | 说明 |
|----------|------|------|
| 密码加密 | ✅ 良好 | 使用 bcrypt |
| SQL 注入防护 | ✅ 良好 | SQLAlchemy ORM 自动参数化 |
| JWT 配置 | ✅ 良好 | 支持生产环境强制密钥验证 |
| 输入验证 | ✅ 良好 | Pydantic Schema 提供类型验证 |
| 权限控制 | ⚠️ 部分问题 | 大部分有检查，存在信息泄露 |
| XSS 防护 | ⚠️ 依赖可选 | bleach 为可选依赖 |
| 验证码机制 | ⚠️ 可改进 | 有次数和过期限制 |

---

## 五、修复优先级

| 优先级 | 问题编号 | 问题描述 | 预计修复时间 |
|--------|----------|----------|--------------|
| **P0** | SEC-001 | 密码重置功能 bug | 10 分钟 |
| **P1** | SEC-002 | 管理员身份泄露 | 30 分钟 |
| **P1** | SEC-003 | 用户名枚举漏洞 | 15 分钟 |
| **P2** | PERF-001 | N+1 查询问题 | 2 小时 |
| **P2** | SEC-004 | bleach 依赖 | 15 分钟 |
| **P3** | DRY-001 | 代码重复 | 4 小时 |

---

## 六、总体评估

| 评估项 | 评分 | 说明 |
|--------|------|------|
| **安全性** | ⭐⭐⭐☆☆ | 中等偏上，存在 2 个严重问题 |
| **代码质量** | ⭐⭐⭐⭐☆ | 良好，存在一些重复代码 |
| **性能** | ⭐⭐⭐☆☆ | 中等，存在 N+1 查询问题 |
| **可维护性** | ⭐⭐⭐⭐☆ | 良好，代码结构清晰 |

### 总体评价

该粉丝社群平台项目整体安全状况**中等偏上**，具备良好的安全基础。主要问题集中在：

1. 🔴 **功能性 bug**：密码重置功能完全不可用
2. 🔴 **信息泄露**：管理员身份通过公开接口暴露
3. 🟠 **可优化**：存在 N+1 查询和代码重复

### 建议措施

1. **立即修复**：密码重置功能 bug（P0）
2. **本周修复**：管理员身份泄露 + 用户名枚举（P1）
3. **计划优化**：N+1 查询、代码重复（P2-P3）

---

## 七、审计声明

本报告基于静态代码分析，实际安全问题需结合渗透测试验证。

---

**审计人员**: AI Code Auditor
**审计日期**: 2026-05-20
**报告版本**: v1.0
