# 第三方账号登录 - 前端功能需求表 v2

> 配套后端文档：《第三方账号登录功能需求表 v2》
> 后端版本：v2.0（含 Mock 模式 + 平台沙盒方案）
> 适用前端：Vue 3 / React / 任意 SPA 框架
> 更新日期：2026-07-26

---

## 一、功能总览

| 功能模块 | 前端职责 |
|---------|---------|
| 第三方登录入口 | 登录页展示「微信/抖音/支付宝」三个按钮 |
| OAuth 授权跳转 | 调用后端 `authorize` 接口，跳转到返回的授权页 URL |
| OAuth 回调处理 | 在 `/oauth/callback/{provider}` 接收 `code` + `state`，调后端 `callback` 完成登录 |
| Mock 授权页（可选） | 后端已内置 Mock 授权页 HTML，前端可不用单独开发；如需自定义样式可调用 `/mock/oauth/{provider}/accounts` 自渲染 |
| 账号绑定 | 个人设置页展示已绑定平台，支持「绑定/解绑」 |
| 绑定查询 | 调用 `/auth/oauth/bindings` 渲染绑定列表 |
| 模式无感切换 | 前端不感知 Mock/真实/沙箱模式，统一逻辑 |

---

## 二、后端接口对接清单

所有第三方登录共用一套接口，通过 `{provider}` 区分平台（`wechat` / `douyin` / `alipay`）。

| 接口 | 方法 | 路径 | 认证 | 请求体/参数 | 响应 |
|------|------|------|------|------------|------|
| 获取授权 URL | GET | `/auth/oauth/{provider}/authorize` | 无 | `?purpose=login\|bind` | `{ "authorize_url": "..." }` |
| 登录回调 | POST | `/auth/oauth/{provider}/callback` | 无 | `{ "code": "...", "state": "..." }` | `{ "access_token": "...", "token_type": "bearer" }` |
| 绑定第三方 | POST | `/auth/oauth/{provider}/bind` | Bearer | `{ "code": "...", "state": "..." }` | `{ "msg": "绑定成功" }` |
| 解绑第三方 | DELETE | `/auth/oauth/{provider}/unbind` | Bearer | 无 | `{ "msg": "解绑成功" }` |
| 查询绑定列表 | GET | `/auth/oauth/bindings` | Bearer | 无 | `[{ "provider": "...", "oauth_uid": "...", "created_at": "..." }]` |
| Mock 授权页 | GET | `/mock/oauth/{provider}` | 无 | `?state=xxx&purpose=login\|bind` | HTML 页面 |
| Mock 测试账号列表 | GET | `/mock/oauth/{provider}/accounts` | 无 | 无 | `{ "provider": "...", "accounts": [...] }` |
| Mock 平台总览 | GET | `/mock/oauth/providers/list` | 无 | 无 | `{ "providers": [...] }` |

---

## 三、新增页面

| 页面 | 路径 | 说明 |
|------|------|------|
| OAuth 回调页 | `/oauth/callback/{provider}` | 接收第三方/Mock 回调的 `code` + `state`，调后端 callback 接口 |
| Mock 授权页（可选） | `/mock/oauth/{provider}` | **后端已内置 HTML 实现**，前端无需重复开发。若需自定义样式可自行实现 |

> 说明：Mock 授权页由后端返回完整 HTML，前端只需 `window.location.href = authorize_url` 跳转过去即可。Mock 模式下 `authorize_url` 会指向 `/mock/oauth/{provider}?state=xxx&purpose=xxx`。

---

## 四、登录页改动

### 4.1 第三方登录按钮

在现有登录表单下方新增「第三方登录」分区：

```
┌────────────────────────────────┐
│  用户名/密码登录表单            │
│  ...                           │
│  [ 登录 ] [ 注册 ]             │
│                                │
│  ─── 其他登录方式 ───          │
│  [ 微信 ]  [ 抖音 ]  [ 支付宝 ] │
└────────────────────────────────┘
```

| 按钮 | 调用接口 | 行为 |
|------|---------|------|
| 微信登录 | `GET /auth/oauth/wechat/authorize?purpose=login` | 跳转返回的 `authorize_url` |
| 抖音登录 | `GET /auth/oauth/douyin/authorize?purpose=login` | 跳转返回的 `authorize_url` |
| 支付宝登录 | `GET /auth/oauth/alipay/authorize?purpose=login` | 跳转返回的 `authorize_url` |

### 4.2 按钮点击统一流程

```javascript
async function handleOAuthLogin(provider) {
  // 1. 调用后端获取授权 URL
  const res = await api.get(`/auth/oauth/${provider}/authorize?purpose=login`);
  // res.data = { authorize_url: "https://..." 或 "/mock/oauth/wechat?state=xxx" }

  // 2. 跳转到授权页（Mock 或真实平台）
  window.location.href = res.data.authorize_url;

  // 3. 用户授权后会被重定向回前端回调页：
  //    /oauth/callback/{provider}?code=xxx&state=xxx
  //    （Mock 模式下 code=mock_{provider}_{index}_{timestamp}）
}
```

---

## 五、OAuth 回调页实现

### 5.1 路由定义

```
/oauth/callback/wechat
/oauth/callback/douyin
/oauth/callback/alipay
```

支持动态路由 `/oauth/callback/:provider`。

### 5.2 回调页逻辑

```javascript
// /oauth/callback/:provider
async function handleCallback() {
  const provider = route.params.provider;
  const code = route.query.code;        // 微信/抖音/Mock 都是 code
  // 注意：支付宝回调参数名是 auth_code，但前端可统一取 code
  const state = route.query.state;

  // 1. 参数校验
  if (!code || !state) {
    showError('授权参数缺失');
    return;
  }

  // 2. 调用后端 callback 接口
  try {
    const res = await api.post(`/auth/oauth/${provider}/callback`, {
      code,
      state,
    });
    // res.data = { access_token, token_type }

    // 3. 保存 token，跳转首页
    authStore.setToken(res.data.access_token);
    await authStore.fetchUserInfo();
    router.push('/');
  } catch (err) {
    // 4. 错误处理
    //    400: state 校验失败 / code 已过期 / Mock code 格式错误
    //    500: 第三方服务不可用
    showError(err.response?.data?.detail || '登录失败');
    setTimeout(() => router.push('/login'), 2000);
  }
}
```

### 5.3 回调页 UI 状态

| 状态 | 展示 |
|------|------|
| 加载中 | "正在完成登录..." + Loading 动画 |
| 成功 | "登录成功，正在跳转..."（1 秒后跳首页） |
| 失败 | 错误信息 + "返回登录" 按钮 |

### 5.4 支付宝回调参数差异

支付宝回调的 query 参数是 `auth_code` 而非 `code`，前端需做兼容：

```javascript
const code = route.query.code || route.query.auth_code;
```

---

## 六、Mock 授权页（后端已内置）

### 6.1 工作机制

后端在 `OAUTH_MOCK_MODE=true` 时，`authorize` 接口返回的 `authorize_url` 会指向后端内置的 Mock 授权页：

```
{OAUTH_FRONTEND_URL}/mock/oauth/{provider}?state=xxx&purpose=login
```

后端 `GET /mock/oauth/{provider}` 直接返回完整 HTML 页面，包含：
- 平台 Logo + 标题
- 测试账号下拉选择框
- "确认授权" 按钮
- 安全提示

### 6.2 前端无需重复开发

前端只需执行 `window.location.href = authorize_url`，跳转后用户在后端渲染的 Mock 页面操作即可。

### 6.3 自定义 Mock 页面（可选）

若前端希望 Mock 授权页与站点风格统一，可自行实现：

1. 调用 `GET /mock/oauth/{provider}/accounts` 获取测试账号列表
2. 自渲染页面，提供账号选择
3. 用户点击"确认授权"后，前端生成 mock code：
   ```javascript
   const timestamp = Math.floor(Date.now() / 1000);
   const mockCode = `mock_${provider}_${accountIndex}_${timestamp}`;
   ```
4. 跳转到 `/oauth/callback/${provider}?code=${mockCode}&state=${state}`

### 6.4 Mock 测试账号（v2 4.2.3）

| 平台 | 序号 | oauth_uid | 昵称 | 头像 |
|------|------|-----------|------|------|
| 微信 | 1 | mock_wechat_openid_001 | 测试微信用户A | https://mock-cdn.test/avatar/wechat_001.png |
| 微信 | 2 | mock_wechat_openid_002 | 测试微信用户B | https://mock-cdn.test/avatar/wechat_002.png |
| 抖音 | 1 | mock_douyin_openid_001 | 测试抖音用户A | https://mock-cdn.test/avatar/douyin_001.png |
| 抖音 | 2 | mock_douyin_openid_002 | 测试抖音用户B | https://mock-cdn.test/avatar/douyin_002.png |
| 支付宝 | 1 | 2088000000000001 | 测试支付宝用户A | https://mock-cdn.test/avatar/alipay_001.png |
| 支付宝 | 2 | 2088000000000002 | 测试支付宝用户B | https://mock-cdn.test/avatar/alipay_002.png |

### 6.5 Mock code 格式

```
mock_{provider}_{account_index}_{timestamp}

示例：
mock_wechat_1_1785060000
mock_douyin_2_1785060000
mock_alipay_1_1785060000
```

有效期 5 分钟，超时后端返回 400。

---

## 七、个人设置页 - 第三方账号绑定

### 7.1 入口

`个人中心 → 账号设置 → 第三方账号绑定`

### 7.2 数据获取

```javascript
// 调用接口获取已绑定列表
const res = await api.get('/auth/oauth/bindings');
// res.data = [
//   { provider: "wechat", oauth_uid: "o6_bmjrPTlm6...", created_at: "2026-07-26T10:00:00" },
//   { provider: "alipay", oauth_uid: "2088...", created_at: "2026-07-26T11:00:00" }
// ]
```

### 7.3 UI 设计

```
┌──────────────────────────────────────────┐
│  第三方账号绑定                           │
├──────────────────────────────────────────┤
│  [微信图标] 微信                          │
│  状态：已绑定（2026-07-26 10:00）        │
│  [ 解绑 ]                                │
├──────────────────────────────────────────┤
│  [抖音图标] 抖音                          │
│  状态：未绑定                             │
│  [ 绑定抖音 ]                            │
├──────────────────────────────────────────┤
│  [支付宝图标] 支付宝                      │
│  状态：已绑定（2026-07-26 11:00）        │
│  [ 解绑 ]                                │
└──────────────────────────────────────────┘
```

### 7.4 绑定流程

```javascript
async function handleBind(provider) {
  // 1. 调用后端获取授权 URL（purpose=bind）
  const res = await api.get(`/auth/oauth/${provider}/authorize?purpose=bind`);

  // 2. 跳转到授权页
  //    注意：跳转前需要保存当前页面路径，绑定完成后跳回
  sessionStorage.setItem('oauth_bind_redirect', window.location.pathname);
  window.location.href = res.data.authorize_url;
}

// 绑定回调页（与登录回调页可复用，但需区分 purpose）
async function handleBindCallback() {
  const provider = route.params.provider;
  const code = route.query.code || route.query.auth_code;
  const state = route.query.state;

  const res = await api.post(`/auth/oauth/${provider}/bind`, { code, state });

  // 跳回设置页
  const redirect = sessionStorage.getItem('oauth_bind_redirect') || '/settings';
  sessionStorage.removeItem('oauth_bind_redirect');
  router.push(redirect);
}
```

### 7.5 解绑流程

```javascript
async function handleUnbind(provider) {
  if (!confirm(`确定要解绑${getProviderName(provider)}账号吗？`)) return;

  try {
    await api.delete(`/auth/oauth/${provider}/unbind`);
    // 刷新绑定列表
    await fetchBindings();
    showToast('解绑成功');
  } catch (err) {
    showToast(err.response?.data?.detail || '解绑失败');
  }
}
```

### 7.6 绑定/解绑状态映射

| 后端响应 | 前端提示 |
|---------|---------|
| 200 `绑定成功` | Toast: "绑定成功" + 刷新列表 |
| 200 `解绑成功` | Toast: "解绑成功" + 刷新列表 |
| 400 `您已绑定了 {provider} 账号，请先解绑` | Toast: "您已绑定该平台账号，请先解绑" |
| 400 `该第三方账号已被其他用户绑定` | Toast: "该账号已被其他用户绑定" |
| 404 `未绑定 {provider} 账号` | Toast: "未绑定该平台账号" |

---

## 八、模式切换无感化

### 8.1 切换矩阵

| 场景 | OAUTH_MOCK_MODE | ALIPAY_SANDBOX | 微信 | 抖音 | 支付宝 |
|------|----------------|----------------|------|------|--------|
| 纯开发调试 | true | false | Mock | Mock | Mock |
| 支付宝真实联调 | true | true | Mock | Mock | 沙箱真实接口 |
| 全部上线 | false | false | 真实接口 | 真实接口 | 真实接口 |

### 8.2 前端无感知

前端代码无需感知当前模式：
- 所有平台均调用 `GET /auth/oauth/{provider}/authorize` 获取 URL
- 后端自动决定返回 Mock 页 URL 还是真实第三方授权页 URL
- 前端只需 `window.location.href = authorize_url`

切换 Mock → 真实时，**前端代码无需任何改动**。

---

## 九、错误处理

### 9.1 全局错误码

| HTTP | 错误信息 | 前端处理 |
|------|---------|---------|
| 400 | 不支持的登录方式: {provider} | 检查 provider 拼写 |
| 400 | State 校验失败，可能存在 CSRF 攻击 | 提示重新发起授权 |
| 400 | State 已过期，请重新发起授权 | 提示重新发起授权 |
| 400 | 授权码无效或已过期 | 提示重新授权 |
| 400 | Mock 授权码已过期，请重新授权 | 提示重新授权 |
| 400 | Mock 授权码格式无效 | 检查 Mock code 生成逻辑 |
| 400 | 该第三方账号已被其他用户绑定 | 提示用户使用其他账号 |
| 400 | 您已绑定了 {provider} 账号，请先解绑 | 引导先解绑 |
| 404 | 未绑定 {provider} 账号 | 刷新绑定列表 |
| 500 | {provider} 登录未配置，请在 .env 中设置 | 联系后端配置 |
| 500 | 第三方服务暂时不可用，请稍后重试 | 提示稍后重试 |
| 500 | 生产环境禁止开启 Mock 模式 | 联系后端修复配置 |

### 9.2 网络异常处理

```javascript
// axios 拦截器统一处理
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 502) {
      // 第三方服务不可用
      showToast('第三方服务暂时不可用，请稍后重试');
    } else if (error.response?.data?.detail) {
      showToast(error.response.data.detail);
    } else {
      showToast('网络异常，请稍后重试');
    }
    return Promise.reject(error);
  }
);
```

---

## 十、Token 管理

### 10.1 Token 存储

OAuth 登录成功后返回的 `access_token` 与普通登录一致，统一处理：

```javascript
// 统一存储
authStore.setToken(res.data.access_token);
// 后续所有请求自动携带 Authorization: Bearer <token>
```

### 10.2 401 全局处理

```javascript
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // token 过期或无效
      authStore.clearToken();
      router.push('/login?redirect=' + encodeURIComponent(route.fullPath));
    }
    return Promise.reject(error);
  }
);
```

---

## 十一、路由守卫

### 11.1 公开路由（无需登录）

- `/login` - 登录页
- `/register` - 注册页
- `/oauth/callback/:provider` - OAuth 回调页
- `/mock/oauth/:provider` - Mock 授权页（后端内置 HTML，前端可不定义此路由）
- 帖子列表、帖子详情等游客可访问页面

### 11.2 受保护路由（需登录）

- `/settings` - 个人设置（含第三方账号绑定）
- `/settings/oauth` - 第三方账号绑定子页
- 其他用户态页面

### 11.3 守卫示例

```javascript
router.beforeEach((to, from, next) => {
  const token = authStore.token;

  // 受保护路由
  if (to.meta.requiresAuth && !token) {
    next(`/login?redirect=${encodeURIComponent(to.fullPath)}`);
    return;
  }

  // 已登录用户访问登录页/注册页，跳转首页
  if (token && ['/login', '/register'].includes(to.path)) {
    next('/');
    return;
  }

  next();
});
```

---

## 十二、UI 规范

### 12.1 平台图标与配色

| 平台 | 主色 | Logo |
|------|------|------|
| 微信 | #07C160 | 微信绿色 logo |
| 抖音 | #000000 | 抖音黑色 logo |
| 支付宝 | #1677FF | 支付宝蓝色 logo |

### 12.2 按钮样式

```css
.oauth-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 1px solid #e0e0e0;
  cursor: pointer;
  transition: all 0.2s;
}
.oauth-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
.oauth-btn--wechat:hover { border-color: #07C160; }
.oauth-btn--douyin:hover { border-color: #000000; }
.oauth-btn--alipay:hover { border-color: #1677FF; }
```

### 12.3 加载状态

所有 OAuth 跳转/回调过程中必须展示 Loading，避免用户重复点击：

```javascript
const loading = ref(false);

async function handleOAuthLogin(provider) {
  if (loading.value) return;
  loading.value = true;
  try {
    const res = await api.get(`/auth/oauth/${provider}/authorize?purpose=login`);
    window.location.href = res.data.authorize_url;
  } catch (err) {
    loading.value = false;
    // ...
  }
}
```

---

## 十三、验收标准（前端侧）

| 编号 | 验收项 | 验收条件 |
|------|-------|---------|
| F1 | 登录页按钮 | 登录页正确展示微信/抖音/支付宝三个登录按钮 |
| F2 | 授权跳转 | 点击按钮调用 authorize 接口并跳转到返回的 URL |
| F3 | Mock 模式跳转 | Mock 模式下跳转到本地 Mock 授权页 |
| F4 | 真实模式跳转 | 真实模式下跳转到对应平台授权页 |
| F5 | 回调页处理 | 回调页正确解析 code + state，调用 callback 接口 |
| F6 | 支付宝参数兼容 | 支付宝回调的 auth_code 能正确解析为 code |
| F7 | 登录成功 | 登录成功后 token 存储、跳转首页、用户信息加载 |
| F8 | 登录失败 | state/code 错误时展示错误提示并引导重试 |
| F9 | 自动注册 | 首次第三方登录后自动创建账号，用户名格式 `{provider}_{nickname}` |
| F10 | 绑定列表 | 个人设置页正确展示三个平台的绑定状态 |
| F11 | 绑定流程 | 点击"绑定"跳转授权 → 回调 → 绑定成功 → 列表刷新 |
| F12 | 解绑流程 | 点击"解绑" → 二次确认 → 调用接口 → 列表刷新 |
| F13 | 重复绑定提示 | 已绑定平台再次绑定时展示"请先解绑" |
| F14 | 跨用户绑定提示 | 第三方账号被其他用户绑定时展示明确提示 |
| F15 | 模式无感切换 | 切换 Mock/真实/沙箱模式时前端代码无需改动 |
| F16 | Loading 状态 | 跳转/回调过程中展示 Loading，禁止重复点击 |
| F17 | 401 全局处理 | token 过期自动跳登录页并保留 redirect |
| F18 | 路由守卫 | 受保护路由未登录时重定向到登录页 |

---

## 十四、注意事项

1. **state 不可前端生成**：state 必须由后端 `authorize` 接口生成并存储，前端只负责透传。
2. **code 不可缓存**：code 是一次性的，使用后立即失效，禁止前端缓存或重放。
3. **支付宝参数名差异**：支付宝回调用 `auth_code`，其他平台用 `code`，前端需兼容。
4. **Mock code 时效**：Mock code 含时间戳，5 分钟过期，前端不要尝试缓存 Mock code。
5. **生产环境 Mock 检查**：后端启动时若检测到 `ENV=production` 且 `OAUTH_MOCK_MODE=true`，会直接拒绝启动。前端不需要处理此情况，但需提示后端修复配置。
6. **跨标签页登录**：OAuth 跳转会离开当前页面，登录成功后回调页应使用 `router.push` 而非 `window.location.reload`，以保留 SPA 状态。
7. **绑定回调与登录回调共用页面**：建议在回调页根据调用上下文（sessionStorage 中是否有 `oauth_bind_redirect`）判断是登录还是绑定，分别调用 `callback` 或 `bind` 接口。
8. **第三方平台图标**：建议使用官方品牌资源包，避免侵权。
9. **Mock 模式视觉提示**：若后端返回的 `authorize_url` 包含 `/mock/oauth/`，前端可在跳转前后展示"当前为 Mock 模式"提示（可选，非必须）。
