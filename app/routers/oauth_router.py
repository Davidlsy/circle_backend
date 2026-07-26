"""
第三方登录 OAuth 路由（v2 新增）

提供统一接口，通过 {provider} 区分平台：wechat / douyin / alipay

接口清单：
  GET  /auth/oauth/{provider}/authorize   获取授权 URL
  POST /auth/oauth/{provider}/callback    登录回调（首次自动注册）
  POST /auth/oauth/{provider}/bind        已登录用户绑定第三方账号
  DELETE /auth/oauth/{provider}/unbind    解绑第三方账号
  GET  /auth/oauth/bindings               查询当前用户已绑定的第三方账号
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import secrets

from app.database import get_db
from app.models import User, OauthAccount
from app.schemas import (
    Token,
    Msg,
    OAuthAuthorizeResponse,
    OAuthCallbackRequest,
    OAuthBindRequest,
    OAuthBindingPublic,
)
from app.auth import (
    get_current_active_user,
    create_access_token,
    hash_password,
)
from app.config import get_settings
from app.logging_config import logger
from app.utils.oauth_helpers import (
    build_authorize_url,
    exchange_code_for_user,
    validate_state,
    validate_provider,
    generate_username_for_oauth,
    is_mock_mode,
    PROVIDER_DISPLAY_NAME,
    SUPPORTED_PROVIDERS,
)

router = APIRouter(prefix="/auth/oauth", tags=["第三方登录"])
settings = get_settings()


# ─── 工具函数 ───

def _find_oauth_account(db: Session, provider: str, oauth_uid: str) -> OauthAccount | None:
    """根据 provider + oauth_uid 查找已绑定的第三方账号"""
    return db.query(OauthAccount).filter(
        OauthAccount.provider == provider,
        OauthAccount.oauth_uid == oauth_uid,
    ).first()


def _find_user_oauth_binding(db: Session, user_id: int, provider: str) -> OauthAccount | None:
    """查找当前用户在指定平台的绑定记录"""
    return db.query(OauthAccount).filter(
        OauthAccount.user_id == user_id,
        OauthAccount.provider == provider,
    ).first()


def _auto_register_user(db: Session, oauth_info) -> User:
    """首次第三方登录时自动创建本站账号。

    - 用户名格式：{provider}_{nickname}
    - 密码：随机字符串（用户不可知，需通过第三方登录）
    - 用户名冲突时追加数字后缀
    """
    base_username = generate_username_for_oauth(oauth_info.provider, oauth_info.nickname)

    # 解决用户名冲突
    username = base_username
    suffix = 1
    while db.query(User).filter(User.username == username).first():
        suffix += 1
        username = f"{base_username}_{suffix}"[:50]

    user = User(
        username=username,
        nickname=oauth_info.nickname,
        avatar_url=oauth_info.avatar,
        hashed_password=hash_password(secrets.token_urlsafe(32)),
    )
    db.add(user)
    db.flush()  # 拿到 user.id

    # 创建 OAuth 绑定记录
    oauth_account = OauthAccount(
        user_id=user.id,
        provider=oauth_info.provider,
        oauth_uid=oauth_info.oauth_uid,
        access_token=oauth_info.access_token,
        refresh_token=oauth_info.refresh_token,
        expires_at=oauth_info.expires_at,
    )
    db.add(oauth_account)
    db.commit()
    db.refresh(user)

    mode_tag = "[MOCK] " if is_mock_mode(oauth_info.provider) else ""
    logger.info(
        f"{mode_tag}自动注册用户: id={user.id}, username={user.username}, "
        f"provider={oauth_info.provider}, oauth_uid={oauth_info.oauth_uid}"
    )
    return user


def _issue_jwt(user: User) -> Token:
    """为本站用户签发 JWT"""
    access_token = create_access_token(data={"sub": user.id})
    return Token(access_token=access_token, token_type="bearer")


# ─── 路由 ───

@router.get("/{provider}/authorize", response_model=OAuthAuthorizeResponse)
def oauth_authorize(provider: str, purpose: str = "login"):
    """获取第三方授权页 URL

    - purpose=login：用于登录（默认）
    - purpose=bind：用于已登录用户绑定账号

    返回的 authorize_url：
    - Mock 模式：本地 Mock 授权页地址
    - 真实模式：第三方平台授权页地址
    """
    validate_provider(provider)
    if purpose not in ("login", "bind"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="purpose 参数仅支持 login / bind",
        )

    authorize_url = build_authorize_url(provider, purpose=purpose)
    return OAuthAuthorizeResponse(authorize_url=authorize_url)


@router.post("/{provider}/callback", response_model=Token)
def oauth_callback(
    provider: str,
    payload: OAuthCallbackRequest,
    db: Session = Depends(get_db),
):
    """OAuth 登录回调

    流程：
    1. 校验 state（CSRF 防护）
    2. 用 code 换取第三方用户信息
    3. 查找已绑定的本站用户 → 直接签发 JWT
    4. 未绑定 → 自动创建本站账号 + 绑定 → 签发 JWT
    """
    validate_provider(provider)
    validate_state(payload.state, provider, purpose="login")

    oauth_info = exchange_code_for_user(payload.code, provider)

    # 查找已绑定账号
    oauth_account = _find_oauth_account(db, oauth_info.provider, oauth_info.oauth_uid)
    if oauth_account:
        user = oauth_account.user
        # 更新 token 信息（便于后续调用第三方接口）
        oauth_account.access_token = oauth_info.access_token
        oauth_account.refresh_token = oauth_info.refresh_token
        oauth_account.expires_at = oauth_info.expires_at
        db.commit()

        mode_tag = "[MOCK] " if is_mock_mode(provider) else ""
        logger.info(f"{mode_tag}OAuth 登录成功(已存在): user_id={user.id}, provider={provider}")
        return _issue_jwt(user)

    # 首次登录：自动注册 + 绑定
    user = _auto_register_user(db, oauth_info)
    return _issue_jwt(user)


@router.post("/{provider}/bind", response_model=Msg)
def oauth_bind(
    provider: str,
    payload: OAuthBindRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """已登录用户绑定第三方账号

    流程：
    1. 校验 state（purpose=bind）
    2. 校验当前用户未绑定该平台
    3. 用 code 换取第三方用户信息
    4. 校验该第三方账号未被其他用户绑定
    5. 创建绑定记录
    """
    validate_provider(provider)
    validate_state(payload.state, provider, purpose="bind")

    # 当前用户是否已绑定该平台
    existing_binding = _find_user_oauth_binding(db, current_user.id, provider)
    if existing_binding:
        platform_name = PROVIDER_DISPLAY_NAME.get(provider, provider)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"您已绑定了 {platform_name} 账号，请先解绑",
        )

    oauth_info = exchange_code_for_user(payload.code, provider)

    # 该第三方账号是否已被其他用户绑定
    other_binding = _find_oauth_account(db, oauth_info.provider, oauth_info.oauth_uid)
    if other_binding and other_binding.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该第三方账号已被其他用户绑定",
        )

    # 创建绑定
    oauth_account = OauthAccount(
        user_id=current_user.id,
        provider=oauth_info.provider,
        oauth_uid=oauth_info.oauth_uid,
        access_token=oauth_info.access_token,
        refresh_token=oauth_info.refresh_token,
        expires_at=oauth_info.expires_at,
    )
    db.add(oauth_account)

    # 同步昵称/头像（仅当本站用户未设置时）
    if not current_user.nickname and oauth_info.nickname:
        current_user.nickname = oauth_info.nickname
    if not current_user.avatar_url and oauth_info.avatar:
        current_user.avatar_url = oauth_info.avatar

    db.commit()

    mode_tag = "[MOCK] " if is_mock_mode(provider) else ""
    logger.info(
        f"{mode_tag}OAuth 绑定成功: user_id={current_user.id}, "
        f"provider={provider}, oauth_uid={oauth_info.oauth_uid}"
    )
    return Msg(msg="绑定成功")


@router.delete("/{provider}/unbind", response_model=Msg)
def oauth_unbind(
    provider: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """解除第三方账号绑定"""
    validate_provider(provider)

    binding = _find_user_oauth_binding(db, current_user.id, provider)
    if not binding:
        platform_name = PROVIDER_DISPLAY_NAME.get(provider, provider)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未绑定 {platform_name} 账号",
        )

    db.delete(binding)
    db.commit()

    mode_tag = "[MOCK] " if is_mock_mode(provider) else ""
    logger.info(
        f"{mode_tag}OAuth 解绑成功: user_id={current_user.id}, provider={provider}"
    )
    return Msg(msg="解绑成功")


@router.get("/bindings", response_model=List[OAuthBindingPublic])
def list_oauth_bindings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """查询当前用户已绑定的第三方账号列表"""
    bindings = db.query(OauthAccount).filter(
        OauthAccount.user_id == current_user.id
    ).all()

    return [
        OAuthBindingPublic(
            provider=b.provider,
            oauth_uid=b.oauth_uid,
            created_at=b.created_at,
        )
        for b in bindings
    ]
