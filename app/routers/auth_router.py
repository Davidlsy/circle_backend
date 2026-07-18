from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, VerificationCode
from app.schemas import (
    UserCreate, UserPublic, Token, Msg,
    ForgotPasswordRequest, ForgotPasswordResponse, ResetPasswordRequest
)
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.config import get_settings, send_verification_email
from app.logging_config import logger
from datetime import timedelta, datetime
import secrets
import string

router = APIRouter(prefix="/auth", tags=["认证"])
settings = get_settings()

# 验证码有效期（分钟）
CODE_EXPIRE_MINUTES = settings.CODE_EXPIRE_MINUTES

# 验证码尝试次数限制（防暴力破解）
MAX_VERIFY_ATTEMPTS = 5  # 单个验证码最大尝试次数


def generate_secure_code(length: int = 6) -> str:
    """
    生成安全的验证码
    - 包含大小写字母和数字
    - 排除易混淆字符（0, O, 1, I, l）
    
    Args:
        length: 验证码长度
        
    Returns:
        str: 验证码
    """
    # 排除易混淆字符
    allowed_chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    excluded_chars = '0O1Il'
    allowed_chars = ''.join(c for c in allowed_chars if c not in excluded_chars)
    
    return ''.join(secrets.choice(allowed_chars) for _ in range(length))


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    用户注册
    - username: 唯一，必填，3-50字符
    - password: 必填，最少6字符
    - email/phone/nickname: 选填
    """
    # 检查用户名是否已存在
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="用户名已被注册")

    # 检查邮箱唯一性（如果提供了）
    if user_data.email and db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    # 检查手机号唯一性（如果提供了）
    if user_data.phone and db.query(User).filter(User.phone == user_data.phone).first():
        raise HTTPException(status_code=400, detail="手机号已被注册")

    # 创建用户
    user = User(
        username=user_data.username,
        email=user_data.email,
        phone=user_data.phone,
        nickname=user_data.nickname or user_data.username,
        hashed_password=hash_password(user_data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    用户登录（OAuth2 兼容方式）
    - username 字段传用户名或邮箱
    - password 字段传密码
    返回 access_token，前端需保存并在请求时加 Header:
      Authorization: Bearer <access_token>
    """
    # 支持 username 或 email 登录
    user = db.query(User).filter(
        (User.username == form_data.username) | (User.email == form_data.username)
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户已被禁用")

    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token)


# ─── 找回密码 ───


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    发起找回密码
    - 凭用户名或邮箱查找用户
    - 生成6位验证码，存库
    - 生产环境：通过邮件发送验证码，API 不返回明文
    - 开发环境：直接返回验证码便于调试
    - 验证码有效期由 CODE_EXPIRE_MINUTES 配置，默认 15 分钟
    """
    user = db.query(User).filter(
        (User.username == request.username) | (User.email == request.username)
    ).first()

    if not user:
        # 用户不存在也返回成功，防止恶意遍历探测用户名
        return ForgotPasswordResponse(
            msg="如果账号存在且已绑定邮箱，验证码已发送",
            code="",
            expires_in_seconds=CODE_EXPIRE_MINUTES * 60
        )

    # 作废该用户同用途的旧验证码
    db.query(VerificationCode).filter(
        VerificationCode.email == user.email,
        VerificationCode.purpose == "reset_password",
        VerificationCode.used == False
    ).update({"used": True})

    # 生成安全的验证码（字母+数字，排除易混淆字符）
    code = generate_secure_code(6)
    hashed_code = hash_password(code)  # 存哈希，不存明文

    verification = VerificationCode(
        email=user.email,
        phone=user.phone,
        code=hashed_code,
        purpose="reset_password",
        expires_at=datetime.utcnow() + timedelta(minutes=CODE_EXPIRE_MINUTES)
    )
    db.add(verification)
    db.commit()

    # 根据环境决定是否发送邮件和返回验证码
    if settings.ENV == "production":
        # 生产环境：发送邮件，不返回验证码
        email_sent = await send_verification_email(
            to_email=user.email,
            code=code,
            expire_minutes=CODE_EXPIRE_MINUTES
        )
        if not email_sent:
            # 邮件发送失败，通知用户
            logger.error(f"验证码邮件发送失败: {user.email}")
            return ForgotPasswordResponse(
                msg="验证码发送失败，请稍后重试或联系客服",
                code="",
                expires_in_seconds=0
            )
        return ForgotPasswordResponse(
            msg="如果账号存在且已绑定邮箱，验证码已发送",
            code="",  # 生产环境不返回验证码
            expires_in_seconds=CODE_EXPIRE_MINUTES * 60
        )
    else:
        # 开发环境：尝试发送邮件（如果配置了 SMTP），同时返回验证码便于调试
        if settings.SMTP_HOST and settings.SMTP_USER:
            await send_verification_email(
                to_email=user.email,
                code=code,
                expire_minutes=CODE_EXPIRE_MINUTES
            )
        return ForgotPasswordResponse(
            msg="如果账号存在且已绑定邮箱，验证码已发送",
            code=code,  # 开发环境返回验证码
            expires_in_seconds=CODE_EXPIRE_MINUTES * 60
        )


@router.post("/reset-password", response_model=Msg)
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    重置密码
    - 验证6位验证码（一次性，15分钟内有效）
    - 验证通过后用新密码替换旧密码
    - 限制尝试次数防止暴力破解
    """
    # 先根据邮箱查找该用户最新的未使用验证码
    # 优化：添加邮箱过滤，减少查询范围
    latest_code = db.query(VerificationCode).filter(
        VerificationCode.email == request.email,  # 添加邮箱过滤
        VerificationCode.used == False,
        VerificationCode.expires_at > datetime.utcnow(),
        VerificationCode.purpose == "reset_password"
    ).order_by(VerificationCode.created_at.desc()).first()

    if not latest_code:
        raise HTTPException(status_code=400, detail="验证码无效或已过期")

    # 检查尝试次数（防暴力破解）
    if latest_code.attempt_count >= MAX_VERIFY_ATTEMPTS:
        # 超过尝试次数，标记为已使用
        latest_code.used = True
        db.commit()
        raise HTTPException(status_code=400, detail="验证码尝试次数过多，请重新获取")

    # 验证验证码
    if not verify_password(request.code, latest_code.code):
        # 验证失败，增加尝试次数
        latest_code.attempt_count = (latest_code.attempt_count or 0) + 1
        db.commit()
        remaining = MAX_VERIFY_ATTEMPTS - latest_code.attempt_count
        raise HTTPException(
            status_code=400, 
            detail=f"验证码错误，还剩 {remaining} 次尝试机会"
        )

    # 找到对应用户
    user = db.query(User).filter(User.email == latest_code.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 更新密码
    user.hashed_password = hash_password(request.new_password)
    latest_code.used = True
    db.commit()

    logger.info(f"用户 {user.email} 密码重置成功")
    return Msg(msg="密码重置成功，请使用新密码登录")
