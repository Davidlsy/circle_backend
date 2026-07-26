"""
Mock 授权页路由（v2 新增）

仅在 OAUTH_MOCK_MODE=true 时可用，生产环境自动禁用。

提供两个接口：
  GET  /mock/oauth/{provider}           返回 Mock 授权页 HTML
  GET  /mock/oauth/{provider}/accounts  返回测试账号列表 JSON（供前端自定义页面使用）

页面行为：
  - 展示平台标识、安全提示
  - 提供测试账号下拉选择
  - 点击"确认授权"后生成 mock_code，重定向到前端 OAuth 回调页
"""
from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import HTMLResponse, JSONResponse
from urllib.parse import urlencode

from app.config import get_settings
from app.logging_config import logger
from app.utils.oauth_helpers import (
    validate_provider,
    generate_mock_code,
    MOCK_TEST_ACCOUNTS,
    PROVIDER_DISPLAY_NAME,
    get_frontend_callback_path,
    SUPPORTED_PROVIDERS,
)

router = APIRouter(prefix="/mock/oauth", tags=["Mock 授权页"])
settings = get_settings()


# ─── 安全拦截：生产环境或非 Mock 模式禁用 ───

def _ensure_mock_mode() -> None:
    """确保当前处于 Mock 模式（生产环境强制关闭）"""
    if settings.ENV == "production":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="生产环境禁止开启 Mock 模式，请设置 OAUTH_MOCK_MODE=false",
        )
    if not settings.OAUTH_MOCK_MODE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mock 模式未开启",
        )


# ─── 平台主题色 ───

PROVIDER_THEME: dict[str, dict[str, str]] = {
    "wechat": {
        "primary": "#07C160",
        "bg": "#f5f5f5",
        "logo_text": "微信",
    },
    "douyin": {
        "primary": "#000000",
        "bg": "#f5f5f5",
        "logo_text": "抖音",
    },
    "alipay": {
        "primary": "#1677FF",
        "bg": "#f5f5f5",
        "logo_text": "支付宝",
    },
}


# ─── 路由 ───

@router.get("/{provider}", response_class=HTMLResponse)
def mock_authorize_page(
    provider: str,
    state: str = Query(..., description="OAuth state，由 /auth/oauth/{provider}/authorize 生成"),
    purpose: str = Query("login", description="login / bind"),
):
    """返回 Mock 授权页 HTML"""
    _ensure_mock_mode()
    validate_provider(provider)
    if purpose not in ("login", "bind"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="purpose 参数仅支持 login / bind",
        )

    theme = PROVIDER_THEME[provider]
    accounts = MOCK_TEST_ACCOUNTS[provider]
    platform_name = PROVIDER_DISPLAY_NAME[provider]

    # 构建确认授权后的回调 URL（前端回调页）
    callback_url = f"{settings.OAUTH_FRONTEND_URL.rstrip('/')}{get_frontend_callback_path(provider)}"

    logger.info(f"[MOCK] 渲染 {provider} 授权页: state={state}, purpose={purpose}")

    return HTMLResponse(content=_render_mock_page(
        provider=provider,
        platform_name=platform_name,
        theme=theme,
        accounts=accounts,
        state=state,
        purpose=purpose,
        callback_url=callback_url,
    ))


@router.get("/{provider}/accounts")
def mock_list_accounts(provider: str):
    """返回指定平台的 Mock 测试账号列表（JSON）

    前端可基于此接口自定义 Mock 授权页样式。
    """
    _ensure_mock_mode()
    validate_provider(provider)
    return {
        "provider": provider,
        "platform_name": PROVIDER_DISPLAY_NAME[provider],
        "accounts": [
            {"index": i + 1, **acc}
            for i, acc in enumerate(MOCK_TEST_ACCOUNTS[provider])
        ],
    }


@router.get("/providers/list")
def mock_list_providers():
    """返回所有支持的第三方平台及测试账号（仅 Mock 模式可用）"""
    _ensure_mock_mode()
    return {
        "providers": [
            {
                "provider": p,
                "platform_name": PROVIDER_DISPLAY_NAME[p],
                "accounts": [
                    {"index": i + 1, **acc}
                    for i, acc in enumerate(MOCK_TEST_ACCOUNTS[p])
                ],
            }
            for p in SUPPORTED_PROVIDERS
        ],
    }


# ─── HTML 渲染 ───

def _render_mock_page(
    provider: str,
    platform_name: str,
    theme: dict[str, str],
    accounts: list[dict[str, str]],
    state: str,
    purpose: str,
    callback_url: str,
) -> str:
    """渲染 Mock 授权页 HTML

    页面行为：
    - 用户从下拉框选择测试账号
    - 点击"确认授权"后，前端 JS 生成 mock_code 并跳转到 callback_url
    """
    primary = theme["primary"]
    bg = theme["bg"]
    logo_text = theme["logo_text"]

    # 构建账号选项
    account_options = "\n".join([
        f'<option value="{i + 1}">{acc["nickname"]} ({acc["oauth_uid"]})</option>'
        for i, acc in enumerate(accounts)
    ])

    purpose_text = "绑定账号" if purpose == "bind" else "登录"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{platform_name} 模拟授权 - Mock OAuth</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background: {bg};
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
  }}
  .container {{
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 2px 16px rgba(0, 0, 0, 0.08);
    width: 100%;
    max-width: 400px;
    overflow: hidden;
  }}
  .warning-bar {{
    background: #fffbe6;
    border-bottom: 1px solid #ffe58f;
    color: #d48806;
    padding: 10px 16px;
    font-size: 13px;
    text-align: center;
    font-weight: 500;
  }}
  .header {{
    padding: 32px 24px 16px;
    text-align: center;
    border-bottom: 1px solid #f0f0f0;
  }}
  .logo {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 64px;
    height: 64px;
    border-radius: 16px;
    background: {primary};
    color: #fff;
    font-size: 24px;
    font-weight: bold;
    margin-bottom: 12px;
  }}
  .header h1 {{
    font-size: 18px;
    color: #333;
    font-weight: 500;
  }}
  .header .subtitle {{
    margin-top: 6px;
    font-size: 13px;
    color: #999;
  }}
  .body {{
    padding: 24px;
  }}
  .field-label {{
    display: block;
    font-size: 13px;
    color: #666;
    margin-bottom: 8px;
  }}
  .field-select {{
    width: 100%;
    padding: 10px 12px;
    border: 1px solid #d9d9d9;
    border-radius: 6px;
    font-size: 14px;
    background: #fff;
    color: #333;
    cursor: pointer;
    outline: none;
    transition: border-color 0.2s;
  }}
  .field-select:focus {{
    border-color: {primary};
  }}
  .auth-info {{
    margin: 16px 0;
    padding: 12px;
    background: #fafafa;
    border-radius: 6px;
    font-size: 12px;
    color: #666;
    line-height: 1.6;
  }}
  .actions {{
    display: flex;
    gap: 12px;
    margin-top: 8px;
  }}
  .btn {{
    flex: 1;
    padding: 10px 16px;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    cursor: pointer;
    transition: opacity 0.2s;
  }}
  .btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
  .btn-primary {{ background: {primary}; color: #fff; }}
  .btn-secondary {{ background: #f0f0f0; color: #666; }}
  .footer {{
    padding: 12px 24px;
    border-top: 1px solid #f0f0f0;
    text-align: center;
    font-size: 12px;
    color: #bbb;
  }}
  .meta {{
    margin-top: 12px;
    font-size: 11px;
    color: #ccc;
    text-align: center;
    word-break: break-all;
  }}
</style>
</head>
<body>
  <div class="container">
    <div class="warning-bar">⚠️ Mock 模式 — 仅供开发调试，请勿用于生产环境</div>

    <div class="header">
      <div class="logo">{logo_text}</div>
      <h1>{platform_name} 模拟授权</h1>
      <div class="subtitle">将使用 {platform_name} 账号{purpose_text}</div>
    </div>

    <div class="body">
      <label class="field-label" for="account">选择测试账号</label>
      <select id="account" class="field-select">
        {account_options}
      </select>

      <div class="auth-info">
        该应用将获取你的以下信息：<br>
        • 昵称、头像<br>
        • 唯一标识（openid / user_id）
      </div>

      <div class="actions">
        <button type="button" class="btn btn-secondary" onclick="window.history.back()">取消</button>
        <button type="button" class="btn btn-primary" id="confirmBtn" onclick="confirmAuth()">确认授权</button>
      </div>

      <div class="meta">
        State: <code>{state}</code><br>
        Purpose: <code>{purpose}</code><br>
        Callback: <code>{callback_url}</code>
      </div>
    </div>

    <div class="footer">Powered by Mock OAuth · 开发模式</div>
  </div>

<script>
  function confirmAuth() {{
    const accountSelect = document.getElementById('account');
    const accountIndex = accountSelect.value;
    const provider = "{provider}";
    const state = "{state}";
    const callbackUrl = "{callback_url}";

    // 生成 mock code：mock_{{provider}}_{{account_index}}_{{timestamp}}
    const timestamp = Math.floor(Date.now() / 1000);
    const mockCode = "mock_" + provider + "_" + accountIndex + "_" + timestamp;

    // 重定向到前端回调页
    const url = callbackUrl + "?code=" + encodeURIComponent(mockCode) + "&state=" + encodeURIComponent(state);
    window.location.href = url;
  }}
</script>
</body>
</html>
"""
