"""
第三方登录 OAuth 工具模块（v2 新增）

支持平台：微信 / 抖音 / 支付宝
支持模式：
  1. Mock 模式：完全本地模拟 OAuth 流程，不调用真实第三方接口
  2. 真实模式：调用第三方 OAuth 接口完成授权登录
  3. 支付宝沙箱：在 Mock 模式下，支付宝可单独走沙箱真实接口

设计原则：
  - 对路由层提供统一的 `build_authorize_url` / `exchange_code_for_user` 接口
  - Mock 与真实分支在 helper 内部隔离，路由层无需感知
  - state 校验、Mock code 解析、生产环境检查均在此模块完成
"""
from __future__ import annotations

import time
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Literal
from urllib.parse import urlencode, quote_plus

from fastapi import HTTPException, status

from app.config import get_settings
from app.logging_config import logger


# ─── 平台常量 ───

ProviderType = Literal["wechat", "douyin", "alipay"]

SUPPORTED_PROVIDERS: tuple[str, ...] = ("wechat", "douyin", "alipay")

# 各平台显示名称（用于日志、Mock 页面、自动注册用户名）
PROVIDER_DISPLAY_NAME: Dict[str, str] = {
    "wechat": "微信",
    "douyin": "抖音",
    "alipay": "支付宝",
}


# ─── Mock 测试账号体系（v2 4.2.3） ───

MOCK_TEST_ACCOUNTS: Dict[str, list[Dict[str, str]]] = {
    "wechat": [
        {
            "oauth_uid": "mock_wechat_openid_001",
            "nickname": "测试微信用户A",
            "avatar": "https://mock-cdn.test/avatar/wechat_001.png",
        },
        {
            "oauth_uid": "mock_wechat_openid_002",
            "nickname": "测试微信用户B",
            "avatar": "https://mock-cdn.test/avatar/wechat_002.png",
        },
    ],
    "douyin": [
        {
            "oauth_uid": "mock_douyin_openid_001",
            "nickname": "测试抖音用户A",
            "avatar": "https://mock-cdn.test/avatar/douyin_001.png",
        },
        {
            "oauth_uid": "mock_douyin_openid_002",
            "nickname": "测试抖音用户B",
            "avatar": "https://mock-cdn.test/avatar/douyin_002.png",
        },
    ],
    "alipay": [
        {
            "oauth_uid": "2088000000000001",
            "nickname": "测试支付宝用户A",
            "avatar": "https://mock-cdn.test/avatar/alipay_001.png",
        },
        {
            "oauth_uid": "2088000000000002",
            "nickname": "测试支付宝用户B",
            "avatar": "https://mock-cdn.test/avatar/alipay_002.png",
        },
    ],
}


# ─── state 管理 ───

# 简易内存存储，单进程开发环境使用；生产环境建议替换为 Redis
# key = state, value = {"provider": ..., "created_at": ..., "purpose": "login"|"bind"}
_STATE_STORE: Dict[str, Dict[str, Any]] = {}
_STATE_EXPIRE_SECONDS = 600  # state 有效期 10 分钟


def generate_state(provider: str, purpose: str = "login") -> str:
    """生成 OAuth state 并存储，用于 CSRF 防护。

    Args:
        provider: 平台标识
        purpose: 用途，login（登录）或 bind（绑定）
    """
    state = secrets.token_urlsafe(16)
    _STATE_STORE[state] = {
        "provider": provider,
        "purpose": purpose,
        "created_at": time.time(),
    }
    # 清理过期 state（简易实现，避免内存泄漏）
    _cleanup_expired_states()
    return state


def validate_state(state: str, provider: str, purpose: str = "login") -> None:
    """校验 state 是否有效且与 provider/purpose 匹配。

    Raises:
        HTTPException 400: state 校验失败
    """
    record = _STATE_STORE.pop(state, None)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State 校验失败，可能存在 CSRF 攻击",
        )

    # 时效校验
    age = time.time() - record["created_at"]
    if age > _STATE_EXPIRE_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State 已过期，请重新发起授权",
        )

    if record["provider"] != provider or record["purpose"] != purpose:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State 与请求参数不匹配",
        )


def _cleanup_expired_states() -> None:
    """清理过期的 state 记录"""
    now = time.time()
    expired = [k for k, v in _STATE_STORE.items() if now - v["created_at"] > _STATE_EXPIRE_SECONDS]
    for k in expired:
        _STATE_STORE.pop(k, None)


# ─── 工具函数 ───

def validate_provider(provider: str) -> None:
    """校验 provider 是否受支持。

    Raises:
        HTTPException 400: 不支持的 provider
    """
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的登录方式: {provider}",
        )


def is_mock_mode(provider: str) -> bool:
    """判断指定平台是否走 Mock 模式。

    支付宝在 ALIPAY_SANDBOX=true 时走沙箱真实接口，不算 Mock。
    """
    settings = get_settings()
    if not settings.OAUTH_MOCK_MODE:
        return False
    # 支付宝沙箱优先
    if provider == "alipay" and settings.ALIPAY_SANDBOX:
        return False
    return True


def get_frontend_callback_path(provider: str) -> str:
    """获取前端 OAuth 回调页路径"""
    return f"/oauth/callback/{provider}"


# ─── 授权 URL 生成 ───

def build_authorize_url(provider: str, purpose: str = "login") -> str:
    """构建授权页 URL（Mock 模式返回本地 Mock 页 URL）。

    Args:
        provider: wechat / douyin / alipay
        purpose: login / bind

    Returns:
        授权页 URL 字符串
    """
    validate_provider(provider)
    settings = get_settings()
    state = generate_state(provider, purpose)

    # Mock 模式：返回本地 Mock 授权页 URL
    if is_mock_mode(provider):
        mock_url = f"{settings.OAUTH_FRONTEND_URL.rstrip('/')}/mock/oauth/{provider}"
        params = urlencode({"state": state, "purpose": purpose})
        logger.info(f"[MOCK] {provider} 授权 URL: {mock_url}?{params}")
        return f"{mock_url}?{params}"

    # 真实模式：按平台拼接授权页 URL
    redirect_uri = f"{settings.OAUTH_FRONTEND_URL.rstrip('/')}{get_frontend_callback_path(provider)}"

    if provider == "wechat":
        return _build_wechat_authorize_url(redirect_uri, state)
    elif provider == "douyin":
        return _build_douyin_authorize_url(redirect_uri, state)
    elif provider == "alipay":
        return _build_alipay_authorize_url(redirect_uri, state)

    # 不可达
    raise HTTPException(status_code=400, detail=f"不支持的登录方式: {provider}")


def _build_wechat_authorize_url(redirect_uri: str, state: str) -> str:
    """构建微信扫码授权页 URL"""
    settings = get_settings()
    if not settings.WECHAT_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="wechat 登录未配置，请在 .env 中设置 WECHAT_CLIENT_ID / WECHAT_CLIENT_SECRET",
        )
    params = {
        "appid": settings.WECHAT_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "snsapi_login",
        "state": state,
    }
    return f"https://open.weixin.qq.com/connect/qrconnect?{urlencode(params)}#wechat_redirect"


def _build_douyin_authorize_url(redirect_uri: str, state: str) -> str:
    """构建抖音扫码授权页 URL"""
    settings = get_settings()
    if not settings.DOUYIN_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="douyin 登录未配置，请在 .env 中设置 DOUYIN_CLIENT_ID / DOUYIN_CLIENT_SECRET",
        )
    params = {
        "client_key": settings.DOUYIN_CLIENT_ID,
        "response_type": "code",
        "scope": "user_info",
        "redirect_uri": redirect_uri,
        "state": state,
    }
    return f"https://open.douyin.com/platform/oauth/connect/?{urlencode(params)}"


def _build_alipay_authorize_url(redirect_uri: str, state: str) -> str:
    """构建支付宝授权页 URL（支持沙箱）"""
    settings = get_settings()
    # 沙箱优先
    if settings.ALIPAY_SANDBOX:
        app_id = settings.ALIPAY_SANDBOX_APP_ID
        if not app_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="alipay 沙箱未配置，请在 .env 中设置 ALIPAY_SANDBOX_APP_ID 等凭证",
            )
        logger.info("[ALIPAY-SANDBOX] 使用沙箱网关")
    else:
        app_id = settings.ALIPAY_APP_ID
        if not app_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="alipay 登录未配置，请在 .env 中设置 ALIPAY_APP_ID / ALIPAY_APP_PRIVATE_KEY / ALIPAY_PUBLIC_KEY",
            )

    params = {
        "app_id": app_id,
        "scope": "auth_user",
        "redirect_uri": redirect_uri,
        "state": state,
    }
    return f"https://openauth.alipay.com/oauth2/publicAppAuthorize.htm?{urlencode(params)}"


# ─── Mock code 处理 ───

def generate_mock_code(provider: str, account_index: int) -> str:
    """生成 Mock code：mock_{provider}_{account_index}_{timestamp}"""
    return f"mock_{provider}_{account_index}_{int(time.time())}"


def parse_mock_code(code: str) -> tuple[str, int, int]:
    """解析 Mock code

    Returns:
        (provider, account_index, timestamp)

    Raises:
        HTTPException 400: Mock code 格式无效
    """
    parts = code.split("_")
    if len(parts) != 4 or parts[0] != "mock":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mock 授权码格式无效",
        )
    try:
        provider = parts[1]
        account_index = int(parts[2])
        timestamp = int(parts[3])
    except (ValueError, IndexError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mock 授权码格式无效",
        )

    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mock 授权码中包含不支持的平台: {provider}",
        )

    # 时效校验
    settings = get_settings()
    age = time.time() - timestamp
    if age > settings.OAUTH_MOCK_CODE_EXPIRE_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mock 授权码已过期，请重新授权",
        )

    return provider, account_index, timestamp


def get_mock_account(provider: str, account_index: int) -> Dict[str, str]:
    """根据 provider 和 account_index 获取 Mock 测试账号信息。

    Raises:
        HTTPException 400: account_index 越界
    """
    accounts = MOCK_TEST_ACCOUNTS.get(provider, [])
    if account_index < 1 or account_index > len(accounts):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mock 测试账号序号无效: {account_index}",
        )
    return accounts[account_index - 1]


# ─── code 换取用户信息 ───

class OAuthUserInfo:
    """统一的第三方用户信息（不依赖 pydantic，便于内部传递）"""

    def __init__(
        self,
        provider: str,
        oauth_uid: str,
        nickname: str,
        avatar: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ):
        self.provider = provider
        self.oauth_uid = oauth_uid
        self.nickname = nickname
        self.avatar = avatar
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at

    def __repr__(self) -> str:
        return f"OAuthUserInfo(provider={self.provider}, oauth_uid={self.oauth_uid}, nickname={self.nickname})"


def exchange_code_for_user(code: str, provider: str) -> OAuthUserInfo:
    """用授权 code 换取第三方用户信息。

    Mock 模式：解析 mock code 返回预设账号信息
    真实模式：调用第三方接口换取 access_token + 用户信息

    Args:
        code: 授权码（Mock 模式为 mock_xxx）
        provider: 平台标识

    Returns:
        OAuthUserInfo 对象
    """
    validate_provider(provider)

    if is_mock_mode(provider):
        return _mock_exchange(code, provider)

    # 真实模式
    if provider == "wechat":
        return _wechat_exchange(code)
    elif provider == "douyin":
        return _douyin_exchange(code)
    elif provider == "alipay":
        return _alipay_exchange(code)

    raise HTTPException(status_code=400, detail=f"不支持的登录方式: {provider}")


# ─── Mock 实现 ───

def _mock_exchange(code: str, provider: str) -> OAuthUserInfo:
    """Mock 模式：解析 mock code 返回测试账号信息"""
    parsed_provider, account_index, timestamp = parse_mock_code(code)
    if parsed_provider != provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mock 授权码平台不匹配: 期望 {provider}, 实际 {parsed_provider}",
        )

    account = get_mock_account(provider, account_index)
    logger.info(f"[MOCK] {provider} 登录: {account['nickname']} ({account['oauth_uid']})")

    return OAuthUserInfo(
        provider=provider,
        oauth_uid=account["oauth_uid"],
        nickname=account["nickname"],
        avatar=account["avatar"],
        access_token=f"mock_access_token_{provider}_{account_index}",
        refresh_token=None,
        expires_at=datetime.utcnow() + timedelta(hours=2),
    )


# ─── 真实模式实现 ───

def _wechat_exchange(code: str) -> OAuthUserInfo:
    """微信：code → access_token → userinfo"""
    import httpx

    settings = get_settings()
    if not settings.WECHAT_CLIENT_ID or not settings.WECHAT_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="wechat 登录未配置，请在 .env 中设置",
        )

    # 换 access_token
    token_url = "https://api.weixin.qq.com/sns/oauth2/access_token"
    token_params = {
        "appid": settings.WECHAT_CLIENT_ID,
        "secret": settings.WECHAT_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            token_resp = client.get(token_url, params=token_params)
            token_data = token_resp.json()
    except Exception as e:
        logger.error(f"[WECHAT] 获取 access_token 失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="第三方服务暂时不可用，请稍后重试",
        )

    if "errcode" in token_data:
        logger.warning(f"[WECHAT] access_token 错误: {token_data}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="授权码无效或已过期",
        )

    access_token = token_data["access_token"]
    openid = token_data["openid"]
    expires_in = token_data.get("expires_in", 7200)
    refresh_token = token_data.get("refresh_token")

    # 获取用户信息
    user_url = "https://api.weixin.qq.com/sns/userinfo"
    user_params = {"access_token": access_token, "openid": openid}
    try:
        with httpx.Client(timeout=10.0) as client:
            user_resp = client.get(user_url, params=user_params)
            user_data = user_resp.json()
    except Exception as e:
        logger.error(f"[WECHAT] 获取用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="第三方服务暂时不可用，请稍后重试",
        )

    if "errcode" in user_data:
        logger.warning(f"[WECHAT] userinfo 错误: {user_data}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="获取微信用户信息失败",
        )

    return OAuthUserInfo(
        provider="wechat",
        oauth_uid=openid,
        nickname=user_data.get("nickname") or f"微信用户_{openid[:8]}",
        avatar=user_data.get("headimgurl"),
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
    )


def _douyin_exchange(code: str) -> OAuthUserInfo:
    """抖音：code → access_token → userinfo"""
    import httpx

    settings = get_settings()
    if not settings.DOUYIN_CLIENT_ID or not settings.DOUYIN_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="douyin 登录未配置，请在 .env 中设置",
        )

    # 换 access_token
    token_url = "https://open.douyin.com/oauth/access_token/"
    token_body = {
        "client_key": settings.DOUYIN_CLIENT_ID,
        "client_secret": settings.DOUYIN_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            token_resp = client.post(token_url, json=token_body)
            token_data = token_resp.json()
    except Exception as e:
        logger.error(f"[DOUYIN] 获取 access_token 失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="第三方服务暂时不可用，请稍后重试",
        )

    data = token_data.get("data")
    if not data or "access_token" not in data:
        logger.warning(f"[DOUYIN] access_token 错误: {token_data}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="授权码无效或已过期",
        )

    access_token = data["access_token"]
    open_id = data["open_id"]
    expires_in = data.get("expires_in", 7200)
    refresh_token = data.get("refresh_token")

    # 获取用户信息
    user_url = "https://open.douyin.com/oauth/userinfo/"
    user_params = {"access_token": access_token, "open_id": open_id}
    try:
        with httpx.Client(timeout=10.0) as client:
            user_resp = client.get(user_url, params=user_params)
            user_data = user_resp.json()
    except Exception as e:
        logger.error(f"[DOUYIN] 获取用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="第三方服务暂时不可用，请稍后重试",
        )

    user_info = user_data.get("data") or {}
    if not user_info:
        logger.warning(f"[DOUYIN] userinfo 错误: {user_data}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="获取抖音用户信息失败",
        )

    return OAuthUserInfo(
        provider="douyin",
        oauth_uid=open_id,
        nickname=user_info.get("nickname") or f"抖音用户_{open_id[:8]}",
        avatar=user_info.get("avatar"),
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
    )


def _alipay_exchange(code: str) -> OAuthUserInfo:
    """支付宝：auth_code → access_token → user.info.share

    支付宝所有请求需 RSA2 签名。如未安装 alipay-sdk，则降级到 Mock 并提示。
    """
    settings = get_settings()

    # 沙箱/生产凭证选择
    if settings.ALIPAY_SANDBOX:
        app_id = settings.ALIPAY_SANDBOX_APP_ID
        private_key = settings.ALIPAY_SANDBOX_APP_PRIVATE_KEY
        public_key = settings.ALIPAY_SANDBOX_PUBLIC_KEY
        gateway = "https://openapi-sandbox.dl.alipaydev.com/gateway.do"
        logger.info("[ALIPAY-SANDBOX] 使用沙箱网关调用 alipay.system.oauth.token")
    else:
        app_id = settings.ALIPAY_APP_ID
        private_key = settings.ALIPAY_APP_PRIVATE_KEY
        public_key = settings.ALIPAY_PUBLIC_KEY
        gateway = "https://openapi.alipay.com/gateway.do"

    if not app_id or not private_key or not public_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="alipay 登录未配置，请在 .env 中设置 ALIPAY_APP_ID / ALIPAY_APP_PRIVATE_KEY / ALIPAY_PUBLIC_KEY",
        )

    try:
        from alipay import AliPay  # type: ignore
    except ImportError:
        logger.error("[ALIPAY] 未安装 alipay-sdk-python，无法调用真实接口")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="支付宝 SDK 未安装，请联系管理员安装 alipay-sdk-python",
        )

    alipay_client = AliPay(
        appid=app_id,
        app_notify_url=None,
        app_private_key_string=private_key,
        alipay_public_key_string=public_key,
        sign_type="RSA2",
        debug=False,
    )

    # 换 access_token
    try:
        token_result = alipay_client.server_api(
            "alipay.system.oauth.token",
            grant_type="authorization_code",
            code=code,
        )
    except Exception as e:
        logger.error(f"[ALIPAY] alipay.system.oauth.token 失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="第三方服务暂时不可用，请稍后重试",
        )

    if "access_token" not in token_result:
        logger.warning(f"[ALIPAY] oauth.token 返回异常: {token_result}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="授权码无效或已过期",
        )

    access_token = token_result["access_token"]
    user_id = token_result.get("user_id")
    refresh_token = token_result.get("refresh_token")
    expires_in = int(token_result.get("expires_in", 7200))

    # 获取用户信息
    try:
        share_result = alipay_client.server_api(
            "alipay.user.info.share",
            auth_token=access_token,
        )
    except Exception as e:
        logger.error(f"[ALIPAY] alipay.user.info.share 失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="第三方服务暂时不可用，请稍后重试",
        )

    if share_result.get("code") != "10000":
        logger.warning(f"[ALIPAY] user.info.share 返回异常: {share_result}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="获取支付宝用户信息失败",
        )

    return OAuthUserInfo(
        provider="alipay",
        oauth_uid=user_id or share_result.get("user_id"),
        nickname=share_result.get("nick_name") or f"支付宝用户_{(user_id or '')[-8:]}",
        avatar=share_result.get("avatar"),
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
    )


# ─── 自动注册用户名生成 ───

def generate_username_for_oauth(provider: str, nickname: str) -> str:
    """为自动注册的第三方用户生成本站用户名。

    格式：{provider}_{nickname}（如 wechat_测试微信用户A）
    避免与现有用户名冲突时追加数字后缀。
    """
    base = f"{provider}_{nickname}"[:50]
    return base
