# 前端 Git 仓库访问指南（后端联调用）

> 本文档供后端开发者访问、克隆、运行前端仓库，以及了解前后端联调的 API 路径约定。

---

## 一、仓库信息

| 项目 | 值 |
|------|-----|
| 仓库名称 | circle_frontend |
| 仓库地址 | https://github.com/Davidlsy/circle_frontend |
| 默认分支 | `main` |
| 技术栈 | Vue 3 + Vite 5 + Pinia + Vue Router 4 + Axios |
| Node 版本要求 | >= 18（推荐 20 LTS） |
| 包管理器 | npm |

---

## 二、克隆与运行

### 2.1 克隆仓库

```bash
git clone https://github.com/Davidlsy/circle_frontend.git
cd circle_frontend
```

### 2.2 切换到指定分支

```bash
# 拉取最新
git fetch origin

# 切换到主分支
git checkout main

# 如需切换到开发分支
git checkout trae/agent-A6ego8
```

### 2.3 安装依赖

```bash
npm install
```

### 2.4 启动开发服务器

```bash
npm run dev
```

启动后访问：`http://localhost:5173`

### 2.5 构建生产包

```bash
npm run build
```

构建产物输出到 `dist/` 目录。

---

## 三、API 代理配置（重要）

前端开发服务器（Vite）内置代理，将前端请求转发到后端，**解决跨域问题**。

### 3.1 当前代理配置

配置文件：`vite.config.js`

```javascript
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, '')
    }
  }
}
```

### 3.2 代理规则说明

| 前端请求路径 | 实际转发到后端的路径 | 说明 |
|-------------|-------------------|------|
| `/api/users/me` | `http://localhost:8000/users/me` | 去掉 `/api` 前缀 |
| `/api/auth/login` | `http://localhost:8000/auth/login` | 去掉 `/api` 前缀 |
| `/api/posts` | `http://localhost:8000/posts` | 去掉 `/api` 前缀 |

> **注意**：前端所有 API 请求统一以 `/api` 开头（通过 axios baseURL 配置），Vite 代理会自动去掉 `/api` 前缀后转发给后端。因此**后端路由无需带 `/api` 前缀**。

### 3.3 后端服务地址

默认代理目标：`http://localhost:8000`

若后端运行在其他地址或端口，修改 `vite.config.js` 中的 `target` 字段即可：

```javascript
target: 'http://localhost:你的端口',
```

---

## 四、Mock 模式联调（OAuth 第三方登录）

第三方登录功能在开发阶段使用后端 Mock 模式。Mock 授权页路径为 `/mock/oauth/{provider}`，需在 Vite 代理中额外配置 `/mock` 路径。

如需联调 OAuth 功能，在 `vite.config.js` 的 `proxy` 中添加：

```javascript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, '')
  },
  '/mock': {
    target: 'http://localhost:8000',
    changeOrigin: true
  }
}
```

> `/mock` 路径**不去掉前缀**，直接透传给后端。

---

## 五、前端 API 调用约定

### 5.1 Axios 实例

配置文件：`src/api/index.js`

```javascript
const api = axios.create({
  baseURL: '/api',        // 统一前缀
  timeout: 15000,
})

// 请求拦截器：自动携带 token
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
```

### 5.2 Token 存储约定

| 项目 | 值 |
|------|-----|
| 存储 key | `token` |
| 存储位置 | `localStorage` |
| Header 格式 | `Authorization: Bearer <token>` |

### 5.3 响应数据约定

前端 axios 响应拦截器直接返回 `res.data`，因此后端响应体即为前端接收的数据。

**成功响应**（直接返回业务数据）：

```json
{
  "id": 1,
  "username": "David",
  "nickname": "大卫"
}
```

**错误响应**（HTTP 状态码非 2xx）：

```json
{
  "detail": "错误描述信息"
}
```

前端通过 `err.response.data.detail` 获取错误信息。

---

## 六、关键目录结构

```
circle_frontend/
├── vite.config.js              # Vite 配置（含代理规则）
├── package.json
├── index.html
├── Direct_ai/                  # 需求文档目录
│   ├── GUEST_ACCESS_REQUIREMENTS.md
│   ├── THIRD_PARTY_LOGIN_FRONTEND_REQUIREMENTS.md
│   └── 第三方账号注册与登录功能需求表（前端）.md
└── src/
    ├── api/
    │   ├── index.js            # Axios 实例 + 拦截器
    │   └── modules/
    │       ├── auth.js         # 注册/登录/获取用户信息
    │       ├── oauth.js        # 第三方登录/绑定/解绑
    │       ├── posts.js        # 帖子相关
    │       ├── social.js       # 关注/用户资料
    │       └── ...
    ├── router/
    │   └── index.js            # 路由配置 + 守卫
    ├── stores/
    │   └── user.js             # 用户状态（Pinia）
    ├── views/                  # 页面组件
    │   ├── LoginView.vue       # 登录页（含第三方登录）
    │   ├── RegisterView.vue    # 注册页（含第三方注册）
    │   ├── OauthCallbackView.vue  # OAuth 回调页
    │   ├── ProfileView.vue     # 个人主页（含第三方绑定）
    │   └── ...
    └── components/             # 通用组件
```

---

## 七、联调检查清单

后端启动后，可按以下步骤验证联调是否正常：

- [ ] 后端服务运行在 `http://localhost:8000`
- [ ] 访问 `http://localhost:8000/docs` 能打开 Swagger 文档
- [ ] 前端 `npm run dev` 启动无报错
- [ ] 浏览器访问 `http://localhost:5173` 能打开首页
- [ ] 前端登录请求能成功代理到后端（查看浏览器 Network 面板，请求状态码 200）
- [ ] 若调试 OAuth 功能，`/mock` 代理已配置，Mock 授权页可正常打开

---

## 八、常见问题

### Q1: 前端请求返回 404？

确认后端路由路径是否与前端调用路径一致。前端发 `/api/users/me`，后端应注册 `/users/me` 路由（不带 `/api`）。

### Q2: 前端请求跨域报错？

开发环境应通过 Vite 代理解决跨域，确认 `vite.config.js` 中 proxy 配置正确，且后端运行在配置的 target 地址。

### Q3: OAuth 授权页跳转后空白？

检查 `vite.config.js` 是否配置了 `/mock` 路径代理。Mock 授权页由后端提供，路径为 `/mock/oauth/{provider}`。

### Q4: 如何切换后端地址？

修改 `vite.config.js` 中 `proxy` 的 `target` 字段，重启 `npm run dev` 即可。

---

## 九、相关仓库

- **后端仓库**：https://github.com/Davidlsy/circle_backend
- **前端仓库**：https://github.com/Davidlsy/circle_frontend
