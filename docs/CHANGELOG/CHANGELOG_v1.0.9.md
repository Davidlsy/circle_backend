# 版本更新日志 v1.0.9

## 概述

本版本引入了 **loguru** 日志库，全面重构了日志系统，实现了请求日志、错误日志和慢查询日志的分类记录，提供更强大、更灵活的日志管理能力。

---

## 主要变更

### 1. 引入 loguru 日志库

**文件**: `requirements.txt`

- 新增依赖: `loguru==0.7.2`
- loguru 是一个现代化的 Python 日志库，提供了比标准库 logging 更简洁的 API 和更强大的功能

### 2. 重构日志配置模块

**文件**: `app/logging_config.py`（完全重写）

#### 2.1 日志分类

| 日志类型 | 文件 | 级别 | 保留时间 | 说明 |
|---------|------|------|---------|------|
| 控制台输出 | stdout | INFO+ | - | 彩色格式化输出，便于开发调试 |
| 访问日志 | `logs/access.log` | INFO | 7天 | 记录所有 HTTP 请求信息 |
| 错误日志 | `logs/error.log` | ERROR | 30天 | 记录所有错误及异常堆栈 |
| 慢查询日志 | `logs/slow_query.log` | WARNING | 7天 | 记录执行时间超过阈值的查询 |

#### 2.2 日志格式

- **控制台输出**: 彩色格式化，包含时间、级别、模块名、函数名、行号
- **访问日志**: `2024-01-15 10:30:45 | INFO     | GET /api/posts | status=200 | time=12.5ms | client=127.0.0.1`
- **错误日志**: 完整堆栈跟踪，支持 `backtrace` 和 `diagnose`
- **慢查询日志**: `2024-01-15 10:30:45 | SLOW QUERY | time=520.3ms | sql=SELECT ...`

#### 2.3 配置参数

通过环境变量配置：

```bash
# 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# 日志目录
LOG_DIR=logs

# 慢查询阈值（毫秒）
SLOW_QUERY_THRESHOLD_MS=500
```

#### 2.4 AppLogger 类

提供统一的日志接口：

```python
logger.info(message, **kwargs)      # 信息日志
logger.warning(message, **kwargs)   # 警告日志
logger.error(message, **kwargs)     # 错误日志
logger.debug(message, **kwargs)     # 调试日志
logger.exception(message, **kwargs) # 异常日志（自动包含堆栈）

# 专用方法
logger.access(method, path, status, duration_ms, client)  # 访问日志
logger.slow_query(sql, duration_ms, params)               # 慢查询日志
```

### 3. 更新异常处理器

**文件**: `app/error_handlers.py`

- 移除标准库 `logging` 导入
- 改用 `from app.logging_config import logger`
- 所有异常处理器使用 loguru logger 记录错误
- 使用 `logger.exception()` 自动捕获异常堆栈

#### 异常日志记录场景

| 异常类型 | 日志级别 | 记录内容 |
|---------|---------|---------|
| AppException（业务异常） | WARNING | 错误码、详情、请求路径、客户端IP |
| RequestValidationError | WARNING | 校验失败的字段、错误信息、客户端IP |
| IntegrityError | ERROR | 数据库约束冲突详情、客户端IP |
| SQLAlchemyError | ERROR | 数据库错误详情、完整堆栈 |
| Exception（未处理异常） | ERROR | 异常详情、完整堆栈 |

### 4. 更新主应用

**文件**: `app/main.py`

- 移除标准库 `logging` 导入
- 移除旧的 `setup_logging()` 调用
- 改用 `from app.logging_config import logger`
- 更新请求日志中间件，使用 `logger.access()` 方法
- 版本号更新: `1.0.8` → `1.0.9`

#### 请求日志中间件

```python
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    
    # 使用 loguru 记录访问日志
    logger.access(
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=process_time,
        client=request.client.host if request.client else "unknown",
    )
    
    response.headers["X-Process-Time"] = f"{process_time:.1f}ms"
    return response
```

---

## 日志文件结构

```
logs/
├── access.log          # HTTP 请求日志
├── access.log.zip      # 轮转压缩的历史日志
├── error.log           # 错误日志
├── error.log.zip       # 轮转压缩的历史日志
└── slow_query.log      # 慢查询日志
```

---

## 使用示例

### 在路由中使用日志

```python
from app.logging_config import logger

@router.get("/posts")
def get_posts():
    logger.info("获取帖子列表")
    # ... 业务逻辑
    logger.debug(f"查询到 {count} 条记录")
    return posts
```

### 记录慢查询

```python
from app.logging_config import logger

start = time.time()
result = db.execute(query)
duration = (time.time() - start) * 1000

# 自动判断是否超过阈值并记录
logger.slow_query(str(query), duration, params)
```

---

## 环境配置建议

### 开发环境

```bash
LOG_LEVEL=DEBUG
LOG_DIR=logs
SLOW_QUERY_THRESHOLD_MS=100
```

### 生产环境

```bash
LOG_LEVEL=INFO
LOG_DIR=/var/log/fan_community
SLOW_QUERY_THRESHOLD_MS=500
```

---

## 与 v1.0.8 的对比

| 特性 | v1.0.8 (标准 logging) | v1.0.9 (loguru) |
|-----|----------------------|-----------------|
| 配置复杂度 | 需要多个 Handler/Formatter | 简洁的 `add()` 方法 |
| 彩色输出 | 需额外配置 | 内置支持 |
| 异常堆栈 | 手动格式化 | 自动 `backtrace` + `diagnose` |
| 日志轮转 | 需单独配置 RotatingFileHandler | 内置 `rotation`/`retention` |
| 异步安全 | 需注意 | 内置支持 |
| 结构化日志 | 需自定义 | 支持 `bind()` 上下文 |

---

## 测试验证

所有 56 个单元测试通过，日志功能正常工作：

```bash
pytest tests/ -v
# 56 passed in 2.34s
```

---

## 版本信息

- **版本号**: 1.0.9
- **发布日期**: 2026-05-12
- **主要功能**: 日志系统重构，引入 loguru
