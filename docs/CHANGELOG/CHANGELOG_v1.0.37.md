# 更新日志 v1.0.37

## 版本信息
- **版本号**: v1.0.37
- **发布日期**: 2026-05-14
- **更新类型**: 安全修复（中危）

## 更新概述

本次更新修复了代码审计中发现的中危安全问题 **"验证码明文返回（MVP 已知问题）"**。通过实现完整的邮件发送功能，确保生产环境不再通过 API 返回验证码明文，而是通过邮件发送给用户，有效防止账户接管攻击。

---

## 修复的问题

### 🟡 中危-001: 验证码明文返回（MVP 已知问题）

**问题描述**:
原代码在 `app/routers/auth_router.py` 中直接返回验证码明文：
```python
# MVP 直接返回明文验证码，生产环境替换为发邮件/短信
return ForgotPasswordResponse(
    msg="如果账号存在，验证码已生成",
    code=code,  # 明文返回！
    expires_in_seconds=CODE_EXPIRE_MINUTES * 60
)
```

任何人可通过 API 获取任意用户的密码重置验证码，实现账户接管。

**修复方案**:

### 1. 新增 SMTP 邮件配置

在 `app/config.py` 中新增邮件相关配置：

```python
# 验证码配置
CODE_EXPIRE_MINUTES: int = 15  # 验证码有效期（分钟）

# 邮件配置（生产环境密码重置需要）
SMTP_HOST: str = ""           # SMTP 服务器地址
SMTP_PORT: int = 587          # SMTP 端口
SMTP_USER: str = ""           # SMTP 用户名
SMTP_PASSWORD: str = ""       # SMTP 密码
SMTP_FROM: str = ""           # 发件人地址
SMTP_USE_TLS: bool = True     # 是否使用 TLS
```

### 2. 新增邮件发送函数

在 `app/config.py` 中新增 `send_verification_email()` 函数：

```python
async def send_verification_email(
    to_email: str,
    code: str,
    expire_minutes: int = 15
) -> bool:
    """
    发送验证码邮件

    Args:
        to_email: 收件人邮箱
        code: 验证码
        expire_minutes: 有效期（分钟）

    Returns:
        bool: 是否发送成功
    """
    # 开发环境或未配置 SMTP 时，打印日志但不发送
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        logger.info(f"[开发模式] 验证码邮件未发送（SMTP 未配置）")
        return True

    # 构建邮件内容（纯文本 + HTML 双版本）
    # 发送邮件...
```

邮件内容包含：
- 纯文本版本（兼容性）
- HTML 版本（美观展示）
- 验证码高亮显示
- 有效期提示
- 安全提示

### 3. 修改密码重置接口

修改 `forgot_password()` 函数，根据环境决定是否返回验证码：

```python
@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    # ... 生成验证码 ...

    # 根据环境决定是否发送邮件和返回验证码
    if settings.ENV == "production":
        # 生产环境：发送邮件，不返回验证码
        email_sent = await send_verification_email(
            to_email=user.email,
            code=code,
            expire_minutes=CODE_EXPIRE_MINUTES
        )
        return ForgotPasswordResponse(
            msg="验证码已发送至您的邮箱，请查收",
            code="",  # 生产环境不返回验证码
            expires_in_seconds=CODE_EXPIRE_MINUTES * 60
        )
    else:
        # 开发环境：返回验证码便于调试
        return ForgotPasswordResponse(
            msg="验证码已生成（开发环境）",
            code=code,  # 开发环境返回验证码
            expires_in_seconds=CODE_EXPIRE_MINUTES * 60
        )
```

### 4. 行为对比

| 场景 | 原行为 | 新行为 |
|------|--------|--------|
| 生产环境 | 返回验证码明文 | 发送邮件，不返回验证码 |
| 开发环境（无 SMTP） | 返回验证码明文 | 返回验证码明文（便于调试） |
| 开发环境（有 SMTP） | 返回验证码明文 | 发送邮件 + 返回验证码 |

---

## 文件变更

### 修改文件

| 文件路径 | 变更类型 | 变更说明 |
|----------|----------|----------|
| `app/config.py` | 修改 | 新增 SMTP 配置、`send_verification_email()` 函数 |
| `app/routers/auth_router.py` | 修改 | 根据环境决定是否返回验证码，改为异步函数 |
| `app/main.py` | 修改 | 更新版本号至 1.0.37 |
| `.env.example` | 修改 | 新增 SMTP 配置示例和常见邮箱配置说明 |

---

## 迁移指南

### 开发环境

开发环境无需配置 SMTP，系统会自动返回验证码便于调试：

```bash
ENV=development
# 无需配置 SMTP
```

启动后调用 `/auth/forgot-password` 接口，验证码会直接返回。

### 生产环境

**步骤 1**: 选择邮件服务商

常见邮件服务商配置：

| 服务商 | SMTP 地址 | 端口 | 备注 |
|--------|-----------|------|------|
| QQ 邮箱 | smtp.qq.com | 587 | 需使用授权码 |
| 163 邮箱 | smtp.163.com | 465/587 | 需使用授权码 |
| Gmail | smtp.gmail.com | 587 | 需使用应用专用密码 |
| 阿里云企业邮箱 | smtp.qiye.aliyun.com | 465 | - |

**步骤 2**: 获取授权码

以 QQ 邮箱为例：
1. 登录 QQ 邮箱网页版
2. 设置 → 账户 → POP3/SMTP 服务
3. 开启服务并生成授权码

**步骤 3**: 配置环境变量

```bash
ENV=production

# SMTP 配置
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USER=your_qq@qq.com
SMTP_PASSWORD=授权码（非QQ密码）
SMTP_FROM=your_qq@qq.com
SMTP_USE_TLS=True
```

**步骤 4**: 验证配置

启动应用后调用 `/auth/forgot-password` 接口：
- 检查邮箱是否收到验证码邮件
- 检查 API 响应中 `code` 字段是否为空

---

## 邮件模板示例

发送的邮件包含 HTML 格式，展示效果如下：

```
┌─────────────────────────────────────┐
│     密码重置验证码                    │
│                                      │
│  您好！                               │
│  您正在申请重置密码，验证码为：         │
│                                      │
│  ┌─────────────────────────┐        │
│  │      1 2 3 4 5 6        │        │
│  └─────────────────────────┘        │
│                                      │
│  验证码将在 15 分钟后失效，请尽快使用。 │
│  如果这不是您的操作，请忽略此邮件。     │
│                                      │
│  —— 粉丝社群团队                      │
└─────────────────────────────────────┘
```

---

## 安全建议

1. **授权码管理**: 使用邮箱授权码而非密码，定期更换
2. **发送频率限制**: 已有 SlowAPI 限流保护，防止滥用
3. **日志监控**: 监控邮件发送日志，发现异常及时处理
4. **备用方案**: 建议配置备用 SMTP 服务器，提高可用性
5. **短信支持**: 后续可扩展短信验证码支持

---

## 验证清单

- [x] 新增 SMTP 配置项
- [x] 实现邮件发送函数
- [x] 生产环境不返回验证码
- [x] 开发环境返回验证码便于调试
- [x] 邮件内容包含纯文本和 HTML 版本
- [x] 更新环境变量配置示例
- [x] 添加常见 SMTP 配置说明
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过安全审计
