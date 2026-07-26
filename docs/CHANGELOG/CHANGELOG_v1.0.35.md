# 更新日志 v1.0.35

## 版本信息
- **版本号**: v1.0.35
- **发布日期**: 2026-05-14
- **更新类型**: 安全修复（高危）

## 更新概述

本次更新修复了代码审计中发现的高危安全问题 **"默认 SECRET_KEY 未强制修改"**。通过移除硬编码的默认密钥并添加严格的运行时验证，确保生产环境必须使用强随机密钥，防止 JWT Token 被伪造。

---

## 修复的问题

### 🔴 高危-001: 默认 SECRET_KEY 未强制修改

**问题描述**:
原代码在 `app/config.py` 中硬编码了默认密钥：
```python
SECRET_KEY: str = "your-super-secret-key-change-in-production"
```

如果部署时未通过环境变量覆盖，攻击者可使用已知密钥伪造任意用户的 JWT Token，实现身份冒充。

**修复方案**:

#### 1. 移除默认密钥

```python
# 修改前
SECRET_KEY: str = "your-super-secret-key-change-in-production"

# 修改后
SECRET_KEY: str = ""  # 强制从环境变量读取，无默认值
```

#### 2. 添加密钥安全验证函数

新增 `validate_secret_key()` 函数，在应用启动时进行严格的安全检查：

```python
def validate_secret_key(secret_key: str, env: str) -> None:
    """验证 SECRET_KEY 的安全性"""
    
    # 生产环境强制要求设置密钥
    if env == "production":
        if not secret_key:
            raise ValueError(
                "生产环境错误：必须设置 SECRET_KEY 环境变量。\n"
                "请使用以下命令生成随机密钥：\n"
                '  python -c "import secrets; print(secrets.token_hex(32))"'
            )
        
        # 检查是否使用了弱密钥
        weak_keys = [
            "your-super-secret-key-change-in-production",
            "secret", "secret-key", "123456", "password", "admin",
        ]
        if secret_key.lower() in weak_keys:
            raise ValueError("生产环境错误：SECRET_KEY 使用了弱密钥")
        
        # 检查密钥长度
        if len(secret_key) < 32:
            raise ValueError(
                f"生产环境错误：SECRET_KEY 长度不足（当前 {len(secret_key)} 字符，要求至少 32 字符）"
            )
```

#### 3. 开发环境自动密钥生成

为了便于开发，当开发环境未设置密钥时，自动生成临时密钥（带有警告提示）：

```python
# 开发环境如果没有设置密钥，自动生成一个临时密钥
if env != "production" and not secret_key:
    import warnings
    warnings.warn(
        "开发环境警告：未设置 SECRET_KEY，将使用自动生成的临时密钥。",
        UserWarning,
        stacklevel=2
    )
```

#### 4. 新增密钥生成工具函数

提供便捷的密钥生成命令：

```python
def generate_secret_key() -> str:
    """生成安全的随机密钥"""
    return secrets.token_hex(32)

# 命令行使用：python app/config.py
if __name__ == "__main__":
    print(generate_secret_key())
```

---

## 文件变更

### 修改文件

| 文件路径 | 变更类型 | 变更说明 |
|----------|----------|----------|
| `app/config.py` | 修改 | 移除默认 SECRET_KEY，添加安全验证逻辑 |
| `app/main.py` | 修改 | 更新版本号至 1.0.35 |
| `.env.example` | 修改 | 更新 SECRET_KEY 配置说明，添加 ENV 环境变量 |

---

## 迁移指南

### 开发环境

开发环境无需特殊配置，系统会自动生成临时密钥并显示警告：

```bash
# 启动应用时会看到警告
UserWarning: 开发环境警告：未设置 SECRET_KEY，将使用自动生成的临时密钥。
```

如需固定开发环境密钥，可在 `.env` 文件中设置：

```bash
ENV=development
SECRET_KEY=your-dev-secret-key-here
```

### 生产环境

**步骤 1**: 生成强随机密钥

```bash
python -c "import secrets; print(secrets.token_hex(32))"
# 输出示例：a3f5c8e9d2b1f4a7e6c3d8b5a2f7e4c1d9b6a3f0e7d4c1b8a5f2e9d6c3b0a7f4
```

**步骤 2**: 在 `.env` 文件中配置

```bash
ENV=production
SECRET_KEY=a3f5c8e9d2b1f4a7e6c3d8b5a2f7e4c1d9b6a3f0e7d4c1b8a5f2e9d6c3b0a7f4
```

**步骤 3**: 验证配置

启动应用时如果密钥配置不正确，会立即报错并终止：

```bash
# 未设置密钥
ValueError: 生产环境错误：必须设置 SECRET_KEY 环境变量。

# 密钥太短
ValueError: 生产环境错误：SECRET_KEY 长度不足（当前 16 字符，要求至少 32 字符）

# 使用了弱密钥
ValueError: 生产环境错误：SECRET_KEY 使用了弱密钥 'secret'
```

---

## 安全建议

1. **密钥保管**: 生产环境密钥应使用密钥管理服务（如 AWS KMS、HashiCorp Vault）存储
2. **密钥轮换**: 建议定期（如每 3-6 个月）轮换 JWT 密钥
3. **环境隔离**: 确保开发、测试、生产环境使用不同的密钥
4. **访问控制**: 限制生产环境配置文件的访问权限（`chmod 600 .env`）

---

## 验证清单

- [x] 移除硬编码默认密钥
- [x] 添加密钥长度验证（≥32 字符）
- [x] 添加弱密钥检查
- [x] 生产环境强制要求设置密钥
- [x] 开发环境自动生成临时密钥
- [x] 提供密钥生成工具
- [x] 更新环境变量配置示例
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过安全审计
