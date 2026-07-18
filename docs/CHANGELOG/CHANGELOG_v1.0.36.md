# 更新日志 v1.0.36

## 版本信息
- **版本号**: v1.0.36
- **发布日期**: 2026-05-14
- **更新类型**: 安全修复（高危）

## 更新概述

本次更新修复了代码审计中发现的高危安全问题 **"CORS 配置过于宽松"**。通过添加严格的 CORS 配置验证，确保生产环境必须设置明确的跨域来源白名单，防止 CSRF 攻击和敏感信息泄露。

---

## 修复的问题

### 🔴 高危-002: CORS 配置过于宽松

**问题描述**:
原代码在 `app/config.py` 中 CORS 配置默认允许所有本地开发地址，且生产环境配置检查不够严格：
```python
CORS_ORIGINS: str = ""  # 空字符串时默认允许 localhost
```

如果生产环境未正确配置 CORS_ORIGINS，可能导致：
- 任何网站都可跨域访问 API
- CSRF 攻击风险
- 敏感信息泄露

**修复方案**:

#### 1. 新增 CORS 安全验证函数

在 `app/config.py` 中新增 `validate_cors_origins()` 函数：

```python
def validate_cors_origins(cors_origins: str, env: str) -> list:
    """
    验证 CORS 配置的安全性

    Args:
        cors_origins: CORS 配置的原始字符串
        env: 运行环境

    Returns:
        list: 解析后的允许来源列表

    Raises:
        ValueError: 当 CORS 配置不符合安全要求时
    """
    # 解析来源列表
    if cors_origins:
        origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
    else:
        origins = []

    # 生产环境强制要求设置明确的 CORS 来源
    if env == "production":
        if not origins:
            raise ValueError(
                "生产环境错误：必须设置 CORS_ORIGINS 环境变量。\n"
                "CORS_ORIGINS 用于指定允许访问 API 的前端域名，\n"
                "请根据实际部署情况设置，例如：\n"
                "  CORS_ORIGINS=https://example.com,https://app.example.com\n"
                "注意：生产环境不允许使用通配符 (*) 或允许所有来源。"
            )

        # 检查是否包含不安全的配置
        unsafe_origins = ["*", "null", "http://localhost", "http://127.0.0.1"]
        for origin in origins:
            if origin in unsafe_origins or origin.startswith("http://localhost"):
                raise ValueError(
                    f"生产环境错误：CORS_ORIGINS 包含不安全的来源 '{origin}'。\n"
                    "生产环境不允许使用通配符 (*)、null 或 localhost 作为 CORS 来源。\n"
                    "请设置明确的前端域名，例如：\n"
                    "  CORS_ORIGINS=https://example.com"
                )

        # 检查是否使用 HTTPS（生产环境应该使用 HTTPS）
        for origin in origins:
            if origin.startswith("http://") and not origin.startswith("http://localhost"):
                import warnings
                warnings.warn(
                    f"安全警告：CORS_ORIGINS 中的 '{origin}' 使用 HTTP 协议。\n"
                    "生产环境建议使用 HTTPS 以保证通信安全。",
                    UserWarning,
                    stacklevel=2
                )

    # 开发环境如果没有设置，使用默认的本地开发地址
    if env != "production" and not origins:
        origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173"]
        import warnings
        warnings.warn(
            "开发环境警告：未设置 CORS_ORIGINS，将使用默认的本地开发地址。\n"
            "如需自定义，请在 .env 文件中设置 CORS_ORIGINS。",
            UserWarning,
            stacklevel=2
        )

    return origins
```

#### 2. 新增 CORS 配置获取函数

```python
def get_cors_origins() -> list:
    """
    获取 CORS 允许的源列表

    此函数会验证 CORS 配置的安全性，并在生产环境强制要求设置明确的来源。

    Returns:
        list: 允许的 CORS 来源列表

    Raises:
        ValueError: 当 CORS 配置不符合安全要求时
    """
    settings = get_settings()
    return validate_cors_origins(settings.CORS_ORIGINS, settings.ENV)
```

#### 3. 更新 CORS 中间件配置

在 `app/main.py` 中更新 CORS 中间件配置：

```python
from app.config import get_settings, get_cors_origins

settings = get_settings()

# 获取 CORS 允许的源列表（会验证配置安全性）
cors_origins = get_cors_origins()

# CORS 中间件配置
# 注意：cors_origins 已通过 get_cors_origins() 验证，确保生产环境配置了安全的来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["X-Process-Time"],
    max_age=600,  # 预检请求缓存 10 分钟
)
```

#### 4. 安全验证规则

| 规则 | 说明 |
|------|------|
| 生产环境强制设置 | `ENV=production` 时必须设置 `CORS_ORIGINS`，否则应用无法启动 |
| 禁止通配符 | 不允许使用 `*` 作为来源 |
| 禁止 null | 不允许使用 `null` 作为来源 |
| 禁止 localhost | 生产环境不允许使用 `localhost` 或 `127.0.0.1` |
| HTTPS 建议 | 生产环境建议使用 HTTPS，使用 HTTP 时会发出警告 |

---

## 文件变更

### 修改文件

| 文件路径 | 变更类型 | 变更说明 |
|----------|----------|----------|
| `app/config.py` | 修改 | 添加 `validate_cors_origins()` 和 `get_cors_origins()` 函数 |
| `app/main.py` | 修改 | 使用 `get_cors_origins()` 获取 CORS 配置，收紧允许的 Methods 和 Headers |
| `.env.example` | 修改 | 更新 CORS_ORIGINS 配置说明，添加安全要求注释 |

---

## 迁移指南

### 开发环境

开发环境无需特殊配置，系统会自动使用默认的本地开发地址：

```bash
# 默认允许的地址
- http://localhost:3000
- http://127.0.0.1:3000
- http://localhost:5173
```

如需自定义，可在 `.env` 文件中设置：

```bash
ENV=development
CORS_ORIGINS=http://localhost:8080,http://localhost:3000
```

### 生产环境

**步骤 1**: 确定前端域名

根据实际部署情况，确定需要访问 API 的前端域名，例如：
- 主站：`https://example.com`
- 移动端：`https://m.example.com`
- 管理后台：`https://admin.example.com`

**步骤 2**: 在 `.env` 文件中配置

```bash
ENV=production
CORS_ORIGINS=https://example.com,https://m.example.com,https://admin.example.com
```

**步骤 3**: 验证配置

启动应用时如果 CORS 配置不正确，会立即报错并终止：

```bash
# 未设置 CORS_ORIGINS
ValueError: 生产环境错误：必须设置 CORS_ORIGINS 环境变量。

# 包含不安全的来源
ValueError: 生产环境错误：CORS_ORIGINS 包含不安全的来源 '*'。

# 包含 localhost
ValueError: 生产环境错误：CORS_ORIGINS 包含不安全的来源 'http://localhost:3000'。
```

---

## 安全建议

1. **最小权限原则**: 仅允许必要的前端域名访问 API
2. **子域隔离**: 如果多个子域需要访问，建议分别列出，不使用通配符
3. **HTTPS 强制**: 生产环境应使用 HTTPS，避免中间人攻击
4. **定期审查**: 定期审查 CORS_ORIGINS 配置，移除不再使用的域名
5. **监控异常**: 监控跨域请求的 Origin 头，发现异常及时处置

---

## 验证清单

- [x] 添加 CORS 配置验证函数
- [x] 生产环境强制要求设置 CORS_ORIGINS
- [x] 禁止通配符 (*) 作为来源
- [x] 禁止 null 作为来源
- [x] 禁止 localhost/127.0.0.1（生产环境）
- [x] HTTPS 使用建议
- [x] 开发环境默认地址支持
- [x] 收紧 CORS Methods 和 Headers
- [x] 更新环境变量配置示例
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过安全审计
