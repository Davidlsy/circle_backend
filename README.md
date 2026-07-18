# 粉丝社群平台 - 技术文档

> 基于 FastAPI + SQLAlchemy + SQLite 的 MVP 后端，支持用户注册登录、帖子发布、评论点赞、关注系统、找回密码。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 框架 | FastAPI |
| ORM | SQLAlchemy |
| 数据库 | SQLite（开发）/ MySQL（生产） |
| 认证 | JWT（OAuth2 Password Bearer） |
| 密码加密 | bcrypt（passlib） |
| API 文档 | Swagger UI（自动生成，访问 `/docs`） |

---

## 项目结构

```
fan_community_backend/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── database.py           # 数据库连接配置
│   ├── config.py             # 环境变量配置
│   ├── auth.py               # JWT / 密码加密 / Token 解析
│   ├── models.py             # SQLAlchemy 数据模型（6张表）
│   ├── schemas.py            # Pydantic 请求/响应模型
│   └── routers/
│       ├── auth_router.py    # 认证模块（注册/登录/找回密码）
│       ├── post_router.py    # 帖子模块（CRUD/评论/点赞）
│       └── follow_router.py  # 关注模块（关注/粉丝/好友）
├── schema.sql                # 原生 SQL 建表脚本
├── er_diagram.html           # 数据库 ER 图（浏览器打开）
├── requirements.txt          # Python 依赖
└── run.py                    # 启动入口
```

---

## 数据库模型

共 **6 张表**，通过 SQLAlchemy ORM 管理。

### 1. users（用户表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| username | VARCHAR(50) UNIQUE | 用户名 |
| email | VARCHAR(100) UNIQUE | 邮箱 |
| phone | VARCHAR(20) UNIQUE | 手机号 |
| hashed_password | VARCHAR(255) | 密码哈希 |
| nickname | VARCHAR(50) | 昵称 |
| avatar_url | VARCHAR(500) | 头像 URL |
| bio | VARCHAR(200) | 个人简介 |
| is_active | BOOLEAN | 是否激活 |
| is_superuser | BOOLEAN | 是否超管 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

**关系：**
- `User.posts` → 一对多 → `Post`（级联删除）
- `User.comments` → 一对多 → `Comment`（级联删除）
- `User.following` → 一对多 → `Follow`（我关注的人）
- `User.followers` → 一对多 → `Follow`（我的粉丝）

---

### 2. posts（帖子表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| title | VARCHAR(200) | 标题 |
| content | TEXT | 正文 |
| author_id | FK → users.id | 作者（级联删除） |
| is_published | BOOLEAN | 是否发布 |
| view_count | INTEGER | 浏览量 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

**关系：**
- `Post.author` → 多对一 → `User`
- `Post.comments` → 一对多 → `Comment`（级联删除）
- `Post.likes` → 一对多 → `Like`（级联删除）

---

### 3. comments（评论表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| content | TEXT | 评论内容 |
| author_id | FK → users.id | 评论者（级联删除） |
| post_id | FK → posts.id | 所属帖子（级联删除） |
| parent_id | FK → comments.id | 父评论（回复功能，可为空） |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

**关系：**
- `Comment.parent` → 自引用（父评论）
- `Comment.replies` → 自引用（子评论列表）
- 支持无限嵌套回复，删除父评论会级联删除所有子评论

---

### 4. likes（点赞表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| user_id | FK → users.id | 点赞用户（级联删除） |
| post_id | FK → posts.id | 被赞帖子（级联删除） |
| created_at | DATETIME | 点赞时间 |

**约束：** `UNIQUE(user_id, post_id)` — 防止重复点赞

---

### 5. follows（关注关系表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| follower_id | FK → users.id | 关注者（谁关注） |
| following_id | FK → users.id | 被关注者（关注谁） |
| created_at | DATETIME | 关注时间 |

**约束：** `UNIQUE(follower_id, following_id)` — 防止重复关注

---

### 6. verification_codes（验证码表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 主键 |
| email | VARCHAR(100) | 关联邮箱 |
| phone | VARCHAR(20) | 关联手机 |
| code | VARCHAR(6) | 验证码（bcrypt 哈希存储） |
| purpose | VARCHAR(20) | 用途，默认 `reset_password` |
| expires_at | DATETIME | 过期时间 |
| used | BOOLEAN | 是否已使用（一次性） |
| created_at | DATETIME | 创建时间 |

---

## API 接口文档

所有接口 Base URL：`http://host/auth`（认证）、`http://host/posts`（帖子）、`http://host/users`（用户/关注）

认证方式：除公开接口外，均需在 Header 中传递：
```
Authorization: Bearer <access_token>
```

---

### 认证模块 `/auth`

#### 注册用户
```
POST /auth/register
Body: {
  "username": "alice",
  "password": "password123",
  "email": "alice@example.com",   // 选填
  "phone": "13800138000",          // 选填
  "nickname": "Alice"              // 选填，默认等于 username
}
Response 201: UserPublic
```

#### 用户登录
```
POST /auth/login
FormData: {
  "username": "alice@example.com",  // 支持 username 或 email
  "password": "password123"
}
Response 200: { "access_token": "xxx", "token_type": "bearer" }
```

#### 发起找回密码
```
POST /auth/forgot-password
Body: { "username": "alice@example.com" }  // 支持 username 或注册邮箱
Response 200: {
  "msg": "如果账号存在，验证码已生成",
  "code": "382917",        // MVP 直接返回明文，生产环境走邮件/短信
  "expires_in_seconds": 900
}
```
**注意：** 用户名不存在时也返回成功，防止恶意枚举攻击。

#### 重置密码
```
POST /auth/reset-password
Body: {
  "code": "382917",
  "new_password": "newpassword123"
}
Response 200: { "msg": "密码重置成功，请使用新密码登录" }
```
**规则：**
- 验证码一次性使用，用完标记 `used=True`
- 15 分钟后自动过期
- 验证码哈希存储，验证时比对哈希值

---

### 帖子模块 `/posts`

#### 创建帖子（需认证）
```
POST /posts/
Header: Authorization: Bearer <token>
Body: {
  "title": "我的第一篇帖子",
  "content": "内容正文...",
  "is_published": true    // 选填，默认 true
}
Response 201: PostPublic
```

#### 获取帖子列表（公开）
```
GET /posts/?page=1&page_size=10&author_id=3
Query: page(默认1), page_size(默认10,最大50), author_id(可选，筛选某用户帖子)
Response 200: {
  "posts": [PostDetail, ...],
  "total": 42,
  "page": 1,
  "page_size": 10
}
```
返回数据包含：作者信息、评论数、点赞数、当前用户是否点赞。

#### 获取帖子详情（公开，自动增加浏览量）
```
GET /posts/{post_id}
Response 200: PostDetail
```

#### 更新帖子（需认证，仅作者）
```
PUT /posts/{post_id}
Body: {
  "title": "新标题",       // 选填
  "content": "新内容",     // 选填
  "is_published": false   // 选填
}
Response 200: PostPublic
```

#### 删除帖子（需认证，仅作者或超管）
```
DELETE /posts/{post_id}
Response 200: { "msg": "帖子已删除" }
```

#### 评论帖子（需认证）
```
POST /posts/{post_id}/comments
Body: {
  "content": "写得不错！",
  "post_id": 1,             // 可省略，URL 参数已指定
  "parent_id": null         // 选填，回复某条评论时填评论ID
}
Response 201: CommentPublic
```

#### 获取评论列表（公开，只返回顶级评论）
```
GET /posts/{post_id}/comments
Response 200: [CommentWithAuthor, ...]
```
返回顶级评论及其作者信息，子评论通过 `parent_id` 关联。

#### 删除评论（需认证，仅作者或超管）
```
DELETE /posts/comments/{comment_id}
Response 200: { "msg": "评论已删除" }
```

#### 点赞/取消点赞（需认证，toggle 模式）
```
POST /posts/{post_id}/like
Response 200: {
  "msg": "点赞成功",
  "liked": true,
  "like_count": 12
}
```
再次调用同一接口即取消点赞。

---

### 用户/关注模块 `/users`

#### 获取当前用户信息（需认证）
```
GET /users/me
Response 200: UserPublic
```

#### 关注/取关用户（需认证，toggle 模式）
```
POST /users/{user_id}/follow
Response 200: {
  "msg": "关注成功",
  "following": true,
  "follower_count": 100,    // 我的粉丝数
  "following_count": 50     // 我的关注数
}
```
不能关注自己。

#### 查看关注关系（公开）
```
GET /users/{user_id}/follow/status
Response 200: {
  "is_following": true,       // 当前用户是否关注了目标用户
  "is_followed_by": false,    // 目标用户是否关注了当前用户
  "follower_count": 100,
  "following_count": 50
}
```
未登录时 `is_following` 和 `is_followed_by` 均为 `false`。

#### 获取用户粉丝列表（公开）
```
GET /users/{user_id}/followers?page=1&page_size=20
Response 200: {
  "users": [UserWithCounts, ...],
  "total": 100
}
```

#### 获取用户关注列表（公开）
```
GET /users/{user_id}/following?page=1&page_size=20
Response 200: {
  "users": [UserWithCounts, ...],
  "total": 50
}
```

#### 获取互相关注的好友列表（需认证）
```
GET /users/me/friends?page=1&page_size=20
Response 200: {
  "users": [UserWithCounts, ...],
  "total": 20
}
```

---

## 通用响应格式

### 成功
```json
// 单对象（由 response_model 决定）
{ "id": 1, "username": "alice", ... }

// 列表（分页）
{
  "posts": [...],
  "total": 42,
  "page": 1,
  "page_size": 10
}

// 通用消息
{ "msg": "帖子已删除" }
```

### 错误
```json
{
  "detail": "帖子不存在"   // 或具体错误信息
}
```

| HTTP 状态码 | 含义 |
|-------------|------|
| 400 | 请求参数错误 |
| 401 | 未认证 / Token 无效 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 422 | Pydantic 验证失败 |
| 500 | 服务器内部错误 |

---

## 启动方式

### 首次启动（初始化数据库）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行数据库迁移（创建所有表）
alembic upgrade head

# 3. 启动开发服务器
python run.py
# 或
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 后续启动

```bash
# 直接启动（数据库已初始化）
python run.py
```

### API 文档
- http://localhost:8000/docs  （Swagger UI）
- http://localhost:8000/       （健康检查）

---

## 数据库迁移（Alembic）

项目使用 Alembic 管理数据库迁移，告别手动改表。

### 常用命令

```bash
# 创建新的迁移脚本（修改模型后执行）
alembic revision --autogenerate -m "描述本次变更"

# 升级数据库到最新版本
alembic upgrade head

# 降级到上一个版本
alembic downgrade -1

# 查看当前版本
alembic current

# 查看历史版本
alembic history
```

### 工作流程

1. **修改模型**（`app/models.py`）
2. **生成迁移脚本**：`alembic revision --autogenerate -m "add xxx field"`
3. **检查生成的脚本**（`alembic/versions/xxx.py`）
4. **执行迁移**：`alembic upgrade head`
5. **验证数据库结构**

### 注意事项

- 自动生成的迁移脚本需要人工检查，确保正确
- 生产环境执行迁移前建议备份数据库
- 团队协作时，迁移脚本需要提交到版本控制

---

## 环境变量（可选）

通过 `app/config.py` 管理，未设置时使用默认值：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| SECRET_KEY | `your-super-secret-key-change-in-production` | JWT 签名密钥 |
| ALGORITHM | `HS256` | JWT 算法 |
| ACCESS_TOKEN_EXPIRE_MINUTES | `10080`（7天） | Token 有效期 |
| DATABASE_URL | `sqlite:///./fan_community.db` | 数据库连接 |
| CORS_ORIGINS | 空字符串 | CORS 允许的前端域名，生产环境必填 |

**CORS_ORIGINS 配置说明：**
- 开发环境：留空或设置 `http://localhost:3000,http://127.0.0.1:3000`
- 生产环境：`CORS_ORIGINS=https://your-frontend.com`，多个域名用逗号分隔

生产环境请修改 `SECRET_KEY` 并设置 `CORS_ORIGINS`。

---

## 生产部署注意事项

1. **CORS**：`CORS_ORIGINS` 必须设置为具体前端域名，禁止使用 `*`
2. **SECRET_KEY**：不要使用默认密钥，设置随机字符串
3. **数据库**：开发用 SQLite，生产切换 MySQL/PostgreSQL
4. **找回密码**：`/auth/forgot-password` 当前直接返回验证码，需接入邮件服务（SendGrid、阿里云邮件等）
5. **超管权限**：`is_superuser=True` 的用户可删除任意帖子/评论

---

*文档版本：v1.0.3 | 生成时间：2026-05-12*
