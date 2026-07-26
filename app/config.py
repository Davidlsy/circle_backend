from pydantic_settings import BaseSettings
from functools import lru_cache
import secrets
import os

# 项目根目录（app/ 的上级目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    # JWT 配置
    # 生产环境必须通过环境变量设置，禁止在生产环境使用默认值
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 天

    # 数据库（使用绝对路径，确保 db 文件始终创建在后端项目的 data/ 目录下）
    _db_path = os.path.join(BASE_DIR, "data", "fan_community.db")
    DATABASE_URL: str = f"sqlite:///{_db_path}"

    # 图片上传配置
    UPLOAD_DIR: str = "uploads"                    # 图片存储目录
    MAX_IMAGE_SIZE: int = 5 * 1024 * 1024          # 单张图片最大 5MB
    MAX_IMAGES_PER_POST: int = 9                    # 单篇帖子最多 9 张图
    ALLOWED_IMAGE_TYPES: list = ["image/jpeg", "image/png", "image/gif", "image/webp"]

    # 视频上传配置
    MAX_VIDEO_SIZE: int = 100 * 1024 * 1024        # 单个视频最大 100MB
    MAX_VIDEOS_PER_POST: int = 3                    # 单篇帖子最多 3 个视频
    MAX_VIDEO_DURATION: int = 300                   # 视频最大时长（秒），默认 5 分钟
    ALLOWED_VIDEO_TYPES: list = ["video/mp4", "video/quicktime", "video/webm", "video/x-msvideo"]
    VIDEO_THUMBNAIL_WIDTH: int = 640               # 视频封面图宽度

    # CORS 配置
    # 生产环境请在 .env 文件中设置具体前端域名，逗号分隔，例如：
    # CORS_ORIGINS=http://localhost:3000,https://example.com
    CORS_ORIGINS: str = ""  # 空字符串表示仅允许本地开发，生产环境必须设置

    # 运行环境
    ENV: str = "development"  # development / production / testing

    # 验证码配置
    CODE_EXPIRE_MINUTES: int = 15  # 验证码有效期（分钟）

    # 审计日志配置
    AUDIT_LOG_DIR: str = "logs/audit"  # 审计日志存储目录
    AUDIT_LOG_RETENTION_DAYS: int = 365  # 审计日志保留天数

    # 邮件配置（生产环境密码重置需要）
    SMTP_HOST: str = ""           # SMTP 服务器地址
    SMTP_PORT: int = 587          # SMTP 端口
    SMTP_USER: str = ""           # SMTP 用户名
    SMTP_PASSWORD: str = ""       # SMTP 密码
    SMTP_FROM: str = ""           # 发件人地址
    SMTP_USE_TLS: bool = True     # 是否使用 TLS

    class Config:
        env_file = ".env"


def validate_secret_key(secret_key: str, env: str) -> None:
    """
    验证 SECRET_KEY 的安全性

    Args:
        secret_key: 配置的密钥
        env: 运行环境

    Raises:
        ValueError: 当密钥不符合安全要求时
    """
    # 生产环境强制要求设置密钥
    if env == "production":
        if not secret_key:
            raise ValueError(
                "生产环境错误：必须设置 SECRET_KEY 环境变量。\n"
                "请使用以下命令生成随机密钥并添加到 .env 文件：\n"
                '  python -c "import secrets; print(secrets.token_hex(32))"\n'
                "然后在 .env 文件中设置：\n"
                "  SECRET_KEY=<生成的随机字符串>"
            )

        # 检查是否使用了弱密钥
        weak_keys = [
            "your-super-secret-key-change-in-production",
            "secret",
            "secret-key",
            "123456",
            "password",
            "admin",
        ]
        if secret_key.lower() in weak_keys:
            raise ValueError(
                f"生产环境错误：SECRET_KEY 使用了弱密钥 '{secret_key}'。\n"
                "请使用强随机字符串作为密钥。"
            )

        # 检查密钥长度
        if len(secret_key) < 32:
            raise ValueError(
                f"生产环境错误：SECRET_KEY 长度不足（当前 {len(secret_key)} 字符，要求至少 32 字符）。\n"
                "请使用以下命令生成安全的随机密钥：\n"
                '  python -c "import secrets; print(secrets.token_hex(32))"'
            )

    # 开发环境如果没有设置密钥，自动生成一个临时密钥（仅用于开发）
    if env != "production" and not secret_key:
        import warnings
        warnings.warn(
            "开发环境警告：未设置 SECRET_KEY，将使用自动生成的临时密钥。\n"
            "建议通过环境变量设置固定密钥以保证开发环境一致性。",
            UserWarning,
            stacklevel=2
        )


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


@lru_cache()
def get_settings() -> Settings:
    """
    获取应用配置（单例）

    首次调用时会验证配置的安全性。

    Returns:
        Settings: 应用配置对象

    Raises:
        ValueError: 当配置不符合安全要求时
    """
    settings = Settings()

    # 验证 SECRET_KEY 安全性
    validate_secret_key(settings.SECRET_KEY, settings.ENV)

    # 如果开发环境未设置密钥，自动生成一个
    if settings.ENV != "production" and not settings.SECRET_KEY:
        # 使用环境名和项目名作为种子，确保同一环境生成相同的密钥
        seed = f"fan_community_dev_{os.path.getmtime(__file__)}"
        settings.SECRET_KEY = secrets.token_hex(32)

    return settings


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


def generate_secret_key() -> str:
    """
    生成安全的随机密钥

    Returns:
        str: 64 字符的十六进制随机字符串
    """
    return secrets.token_hex(32)


def validate_smtp_config(settings: Settings) -> None:
    """
    验证 SMTP 配置（生产环境密码重置功能需要）

    Args:
        settings: 应用配置对象

    Raises:
        ValueError: 当 SMTP 配置不完整时
    """
    if settings.ENV == "production":
        required_fields = [
            ("SMTP_HOST", settings.SMTP_HOST),
            ("SMTP_USER", settings.SMTP_USER),
            ("SMTP_PASSWORD", settings.SMTP_PASSWORD),
            ("SMTP_FROM", settings.SMTP_FROM),
        ]
        missing = [name for name, value in required_fields if not value]
        if missing:
            raise ValueError(
                f"生产环境错误：密码重置功能需要配置 SMTP。\n"
                f"缺少以下配置：{', '.join(missing)}\n"
                "请在 .env 文件中配置 SMTP 相关环境变量。"
            )


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
    settings = get_settings()

    # 开发环境或未配置 SMTP 时，打印日志但不发送
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        from app.logging_config import logger
        logger.info(
            f"[开发模式] 验证码邮件未发送（SMTP 未配置）\n"
            f"  收件人: {to_email}\n"
            f"  验证码: {code}\n"
            f"  有效期: {expire_minutes} 分钟"
        )
        return True

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        # 构建邮件内容
        message = MIMEMultipart("alternative")
        message["Subject"] = "【粉丝社群】密码重置验证码"
        message["From"] = settings.SMTP_FROM
        message["To"] = to_email

        # 纯文本版本
        text_content = f"""
您好！

您正在申请重置密码，验证码为：{code}

验证码将在 {expire_minutes} 分钟后失效，请尽快使用。

如果这不是您的操作，请忽略此邮件。

—— 粉丝社群团队
"""
        # HTML 版本
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: #f5f5f5; padding: 20px; border-radius: 10px;">
        <h2 style="color: #333; margin-bottom: 20px;">密码重置验证码</h2>
        <p style="color: #666; margin-bottom: 10px;">您好！</p>
        <p style="color: #666; margin-bottom: 20px;">您正在申请重置密码，验证码为：</p>
        <div style="background: #fff; padding: 15px; border-radius: 5px; text-align: center; margin-bottom: 20px;">
            <span style="font-size: 32px; font-weight: bold; color: #007bff; letter-spacing: 5px;">{code}</span>
        </div>
        <p style="color: #999; font-size: 14px;">验证码将在 {expire_minutes} 分钟后失效，请尽快使用。</p>
        <p style="color: #999; font-size: 14px; margin-top: 20px;">如果这不是您的操作，请忽略此邮件。</p>
        <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
        <p style="color: #999; font-size: 12px;">—— 粉丝社群团队</p>
    </div>
</body>
</html>
"""
        message.attach(MIMEText(text_content, "plain", "utf-8"))
        message.attach(MIMEText(html_content, "html", "utf-8"))

        # 发送邮件
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, to_email, message.as_string())

        from app.logging_config import logger
        logger.info(f"验证码邮件发送成功: {to_email}")
        return True

    except Exception as e:
        from app.logging_config import logger
        logger.error(f"验证码邮件发送失败: {to_email}, 错误: {e}")
        return False


if __name__ == "__main__":
    # 命令行生成密钥
    print("生成安全的随机密钥：")
    print(generate_secret_key())
