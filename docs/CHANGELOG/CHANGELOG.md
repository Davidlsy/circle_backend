# 粉丝社群平台 - 变更日志 / CHANGELOG

---

## v1.0.8 - 全局异常处理 & 结构化日志

> **版本：** v1.0.8
> **日期：** 2026-05-12
> **功能：** 全局异常处理 + 结构化日志
> **问题类型：** 工程化改进（P1）

---

## 一、问题背景

在 v1.0.7 及之前版本中，项目存在以下问题：

1. **无全局异常处理**：未捕获的异常会返回 FastAPI 默认的 HTML 错误页面，前端难以解析
2. **错误响应格式不统一**：不同路由返回的错误格式各异，前端需要分别处理
3. **无结构化日志**：缺少请求日志和错误日志，线上问题排查困难
4. **无性能监控**：无法追踪每个请求的耗时

---

## 二、修改内容

### 1. 自定义异常类（新建）

**文件：** `app/exceptions.py`

提供统一的业务异常体系：

| 异常类 | HTTP 状态码 | error_code | 说明 |
|--------|-----------|------------|------|
| `AppException` | 自定义 | 自定义 | 基础异常类 |
| `NotFoundException` | 404 | `NOT_FOUND` | 资源不存在 |
| `BadRequestException` | 400 | `BAD_REQUEST` | 请求参数错误 |
| `UnauthorizedException` | 401 | `UNAUTHORIZED` | 未认证 |
| `ForbiddenException` | 403 | `FORBIDDEN` | 无权限 |
| `ConflictException` | 409 | `CONFLICT` | 资源冲突 |
| `RateLimitException` | 429 | `RATE_LIMITED` | 请求频率超限 |

使用示例：
```python
from app.exceptions import NotFoundException, ForbiddenException

# 抛出异常
raise NotFoundException(detail="帖子不存在")
raise ForbiddenException(detail="无权编辑他人帖子")
```

---

### 2. 全局异常处理器（新建）

**文件：** `app/error_handlers.py`

注册 5 个异常处理器，覆盖所有异常场景：

| 处理器 | 捕获异常 | 返回状态码 | 日志级别 |
|--------|---------|-----------|---------|
| `app_exception_handler` | `AppException` | 自定义 | WARNING |
| `validation_exception_handler` | `RequestValidationError` | 422 | WARNING |
| `integrity_error_handler` | `IntegrityError` | 409 | ERROR |
| `sqlalchemy_error_handler` | `SQLAlchemyError` | 500 | ERROR |
| `global_exception_handler` | `Exception` | 500 | ERROR |

---

### 3. 统一错误响应格式

所有错误响应使用统一格式：

```json
{
    "success": false,
    "error": {
        "code": "NOT_FOUND",
        "message": "帖子不存在",
        "detail": {}
    }
}
```

**各场景示例：**

业务异常（404）：
```json
{
    "success": false,
    "error": {
        "code": "NOT_FOUND",
        "message": "帖子不存在"
    }
}
```

参数校验失败（422）：
```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "body -> password: String should have at least 6 characters",
        "detail": [
            {
                "loc": ["body", "password"],
                "msg": "String should have at least 6 characters",
                "type": "string_too_short"
            }
        ]
    }
}
```

数据库完整性错误（409）：
```json
{
    "success": false,
    "error": {
        "code": "INTEGRITY_ERROR",
        "message": "数据重复，请检查唯一字段",
        "detail": "UNIQUE constraint failed: users.username"
    }
}
```

服务器内部错误（500）：
```json
{
    "success": false,
    "error": {
        "code": "INTERNAL_ERROR",
        "message": "服务器内部错误，请稍后重试"
    }
}
```

---

### 4. 结构化日志（新建）

**文件：** `app/logging_config.py`

日志格式：
```
2026-05-12 11:41:05 | INFO     | app                  | 日志系统初始化完成 | level=INFO
2026-05-12 11:41:10 | INFO     | app                  | POST /auth/login | status=200 | time=45.2ms | client=127.0.0.1
2026-05-12 11:41:15 | WARNING | app                  | 业务异常 [NOT_FOUND] 帖子不存在 | path=/posts/999 | client=127.0.0.1
2026-05-12 11:41:20 | ERROR    | app                  | 未处理异常 | path=/posts | error=... | client=127.0.0.1
```

日志级别策略：
- `INFO`：正常请求日志（方法、路径、状态码、耗时、客户端 IP）
- `WARNING`：业务异常、参数校验失败
- `ERROR`：数据库错误、未处理异常（含完整堆栈）

第三方库日志降噪：
- `uvicorn.access` → WARNING
- `sqlalchemy.engine` → WARNING

---

### 5. 请求日志中间件

**文件：** `app/main.py`

每个请求自动记录：
- 请求方法（GET/POST/PUT/DELETE）
- 请求路径
- 响应状态码
- 处理耗时（毫秒）
- 客户端 IP

响应头新增 `X-Process-Time` 字段，方便前端监控接口性能。

---

## 三、使用方式

### 抛出业务异常

在路由中使用自定义异常替代直接返回错误：

**修改前：**
```python
if not post:
    return JSONResponse(status_code=404, content={"detail": "帖子不存在"})
```

**修改后：**
```python
from app.exceptions import NotFoundException

if not post:
    raise NotFoundException(detail="帖子不存在")
```

### 日志配置

默认 INFO 级别，可通过环境变量调整：

```bash
# 开发环境（详细日志）
LOG_LEVEL=DEBUG python run.py

# 生产环境（仅警告和错误）
LOG_LEVEL=WARNING python run.py
```

---

## 四、影响分析

| 影响项 | 说明 |
|--------|------|
| API 版本 | 从 1.0.7 升级到 1.0.8 |
| 错误响应格式 | ⚠️ 变更：所有错误响应统一为 `{"success": false, "error": {...}}` 格式 |
| 功能变更 | 无 |
| 向后兼容 | ⚠️ 部分不兼容：前端需要适配新的错误响应格式 |
| 性能影响 | 极小（每个请求增加约 0.1ms 日志开销） |
| 已有测试 | ✅ 56 passed，全部通过 |

---

## 五、前端适配指南

如果前端之前依赖 FastAPI 默认的错误格式，需要适配新格式：

**旧格式（FastAPI 默认）：**
```json
{"detail": "帖子不存在"}
```

**新格式（统一）：**
```json
{
    "success": false,
    "error": {
        "code": "NOT_FOUND",
        "message": "帖子不存在"
    }
}
```

建议前端封装统一的错误处理：

```javascript
// 响应拦截器
if (response.data.success === false) {
    const error = response.data.error;
    showToast(error.message);  // 显示用户友好的错误信息
}
```

---

## 六、相关文件

| 文件 | 变更 |
|------|------|
| `app/exceptions.py` | **新建**，自定义异常类 |
| `app/error_handlers.py` | **新建**，全局异常处理器 |
| `app/logging_config.py` | **新建**，结构化日志配置 |
| `app/main.py` | 注册异常处理器、请求日志中间件、版本号 1.0.8 |

---

## 七、测试验证

1. **已有测试全部通过**
   ```
   56 passed, 0 failed ✅
   ```

2. **验证统一错误响应**
   ```bash
   # 访问不存在的帖子
   curl http://localhost:8000/posts/99999
   # 应返回 {"success": false, "error": {"code": "NOT_FOUND", ...}}

   # 参数校验失败
   curl -X POST http://localhost:8000/auth/register -H "Content-Type: application/json" -d '{"username":"ab"}'
   # 应返回 {"success": false, "error": {"code": "VALIDATION_ERROR", ...}}
   ```

3. **验证请求日志**
   ```bash
   # 启动服务后，每个请求应输出日志
   # 2026-05-12 11:41:10 | INFO | app | POST /auth/login | status=200 | time=45.2ms | client=127.0.0.1
   ```

---

---

# 历史版本

## v1.0.7 - 添加单元测试 & 修复 JWT Token Bug

> **版本：** v1.0.7
> **日期：** 2026-05-12
> **功能：** 单元测试 + Bug 修复

### 修改内容
- 添加 56 个单元测试（认证模块 + 权限控制）
- 修复 JWT Token `sub` 类型 Bug

---

## v1.0.6 - 引入 Alembic 数据库迁移工具

> **版本：** v1.0.6
> **日期：** 2026-05-12
> **功能：** 数据库迁移管理

---

## v1.0.5 - 代码规范：修复 feed_router 内部 import

> **版本：** v1.0.5
> **日期：** 2026-05-12

---

## v1.0.4 - 代码清理：移除 /auth/me 空实现

> **版本：** v1.0.4
> **日期：** 2026-05-12

---

## v1.0.3 - CORS 安全加固 & Bug 修复

> **版本：** v1.0.3
> **日期：** 2026-05-12

---

## v1.0.2 - 用户资料功能补丁

> **版本：** v1.0.2
> **日期：** 2026-04-17

---

## v1.0.0 - 内容审核功能

> **版本：** v1.0.0
> **日期：** 2026-04-17
