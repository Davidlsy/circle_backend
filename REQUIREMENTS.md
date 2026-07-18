# 粉丝社群平台 - 需求文档

> **项目代号：** FanCommunity  
> **当前版本：** v1.0.2（用户资料功能补丁）  
> **编写日期：** 2026-04-17  
> **状态：** 功能开发完成

---

## 一、项目概述

### 1.1 项目背景

打造一个以粉丝为核心的社区平台，支持用户发帖、互动（评论、点赞、收藏）、社交（关注、私信），形成粉丝社群闭环。

### 1.2 项目目标

- 为粉丝提供一个可注册、发帖、互动的社区空间
- 支持粉丝与粉丝之间的关注社交关系
- 支持用户间一对一私信
- 支持内容审核工作流
- 为后续功能迭代（活动、打赏、直播等）打下基础

### 1.3 目标用户

| 角色 | 描述 |
|------|------|
| 普通用户 | 在平台上注册、消费内容、发帖、互动的粉丝 |
| 内容创作者 | 持续发布内容的活跃用户 |
| 管理员 | 平台运营人员，拥有内容审核和全局管理权限 |

---

## 二、技术架构

### 2.1 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| ORM | SQLAlchemy |
| 数据库 | SQLite（开发）/ MySQL（生产） |
| 认证 | JWT（OAuth2 Password Bearer） |
| 密码加密 | bcrypt（passlib） |
| 静态文件 | FastAPI StaticFiles（本地）/ CDN（生产） |
| API 文档 | Swagger UI（自动生成，访问 `/docs`） |

### 2.2 项目结构

```
fan_community_backend/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── database.py           # 数据库连接配置
│   ├── config.py             # 环境变量配置
│   ├── auth.py               # JWT / 密码加密 / Token 解析
│   ├── models.py             # SQLAlchemy 数据模型（10张表）
│   ├── schemas.py            # Pydantic 请求/响应模型
│   └── routers/
│       ├── auth_router.py    # 认证（注册/登录/找回密码）
│       ├── post_router.py    # 帖子（CRUD/评论/点赞/图片/收藏）
│       ├── follow_router.py  # 关注（关注/粉丝/好友）
│       ├── feed_router.py    # 动态流
│       ├── message_router.py # 私信
│       ├── tag_router.py     # 话题/标签
│       └── audit_router.py   # 内容审核（管理员）
├── schema.sql                # 原生 SQL 建表脚本
├── er_diagram.html           # 数据库 ER 图
├── requirements.txt          # Python 依赖
└── run.py                    # 启动入口
```

---

## 三、数据模型

### 3.1 数据库表（共 10 张）

| 表名 | 说明 | 主键 |
|------|------|------|
| users | 用户 | id |
| posts | 帖子 | id |
| comments | 评论 | id |
| likes | 点赞 | id |
| follows | 关注关系 | id |
| collections | 收藏 | id |
| verification_codes | 验证码 | id |
| post_images | 帖子图片 | id |
| conversations | 私信会话 | id |
| messages | 私信消息 | id |
| tags | 话题/标签 | id |
| post_tags | 帖子-话题关联 | id |

### 3.2 核心关系

```
User (1) ─── (N) Post      ← 作者发布帖子（含 status: pending/approved/rejected）
User (1) ─── (N) Comment   ← 用户发表评论（含 status 审核状态）
Post  (1) ─── (N) Comment  ← 帖子容纳评论
Comment (1) ─ (N) Comment  ← 评论回复评论（自引用 parent_id）
User (1) ─── (N) Like     ← 用户点赞帖子
User (1) ─── (N) Collection← 用户收藏帖子
User (1) ─── (N) Follow   ← 关注关系（following 方向）
User (1) ─── (N) Conversation ← 私信会话
Conversation (1) ─ (N) Message ← 会话包含消息
Post (N) ─── (N) Tag       ← 通过 PostTag 关联
```

### 3.3 级联删除规则

| 被删除 | 级联删除 |
|--------|----------|
| User | 其所有 posts / comments / likes / follows / collections / conversations / messages |
| Post | 其所有 comments / likes / images / collections / post_tags |
| Comment | 其所有子评论（通过 parent_id） |
| Follow / Like / Collection | 关系自动解除 |

### 3.4 唯一约束

| 表 | 约束字段 |
|----|----------|
| users | username / email / phone |
| likes | (user_id, post_id) |
| follows | (follower_id, following_id) |
| collections | (user_id, post_id) |
| tags | name |
| post_tags | (post_id, tag_id) |

---

## 四、功能需求

### 4.1 用户注册与认证

#### US-001：用户注册

| 字段 | 类型 | 约束 |
|------|------|------|
| 用户名 | string | 必填，3-50字符，唯一 |
| 密码 | string | 必填，6-128字符 |
| 邮箱 | string | 选填，唯一 |
| 手机号 | string | 选填，唯一 |
| 昵称 | string | 选填，默认等于用户名 |

**验收标准：**
- 用户名/邮箱/手机号重复时返回明确错误提示
- 注册成功后返回用户信息（不含密码）
- 密码以 bcrypt 哈希存储

---

#### US-002：用户登录

**验收标准：**
- 支持用户名或邮箱 + 密码登录
- 登录成功返回 JWT access_token
- 用户名或密码错误返回 401
- 被禁用用户（is_active=False）禁止登录
- Token 有效期默认 7 天

---

#### US-003：找回密码

**流程：**
1. 用户提交用户名或注册邮箱 → `POST /auth/forgot-password`
2. 系统生成 6 位数字验证码，存入数据库（哈希存储），有效期 15 分钟
3. MVP 直接返回验证码明文；生产环境应接入邮件/短信服务
4. 用户提交验证码 + 新密码 → `POST /auth/reset-password`
5. 验证通过后更新密码，验证码作废

**安全设计：**
- 用户不存在时也返回"验证码已生成"（防用户名枚举）
- 重复申请验证码时自动作废旧码
- 验证码用 bcrypt 哈希存储
- 验证码一次性使用

---

### 4.2 帖子模块

#### US-004：发布帖子

| 字段 | 类型 | 约束 |
|------|------|------|
| 标题 | string | 必填，1-200字符 |
| 内容 | string | 必填，最少 1 字符 |
| 是否发布 | boolean | 选填，默认 true |

**内容审核：**
- 普通用户发布的帖子默认 `status=pending`（待审核）
- 管理员发布的帖子默认 `status=approved`（直接通过）

**验收标准：**
- 未登录用户不能发帖（返回 401）
- 帖子创建成功后返回帖子信息，含创建时间、审核状态
- 作者字段自动填充为当前登录用户

---

#### US-005：浏览帖子列表

**验收标准：**
- 默认按发布时间倒序排列
- 支持分页（默认每页 10 条，最大 50 条）
- 支持按作者筛选（`author_id` 参数）
- 普通用户只能看到 `status=approved` 的帖子；作者本人可看自己的所有状态帖子
- 返回数据包含：帖子信息、作者信息、评论数、点赞数、收藏数、是否点赞、是否收藏、图片列表、标签列表

---

#### US-006：查看帖子详情

**验收标准：**
- 每次访问自动将 `view_count +1`
- 未审核帖子（`pending`/`rejected`）仅作者和管理员可见
- 返回完整帖子内容、作者信息及所有关联数据
- 帖子不存在时返回 404

---

#### US-007：编辑帖子

**验收标准：**
- 仅作者本人可编辑（返回 403）
- 支持部分更新
- 编辑后帖子重新进入待审核状态（`status=pending`）

---

#### US-008：删除帖子

**验收标准：**
- 作者本人可删除
- 管理员可删除任意帖子
- 删除时自动删除关联的本地图片文件
- 删除帖子时自动级联删除所有关联评论、点赞、收藏、图片

---

#### US-009：图片上传

| 参数 | 说明 |
|------|------|
| 单张大小 | 最大 5MB |
| 格式 | jpeg / png / gif / webp |
| 每帖上限 | 9 张 |
| 访问方式 | `/uploads/{filename}` |

**验收标准：**
- 仅帖子作者和管理员可上传
- 上传后自动扣除剩余可上传数量
- 已有的图片不计入新上传数量限制
- 图片 URL 通过静态文件服务访问
- 删除帖子时自动删除本地图片文件

---

#### US-010：删除单张图片

**验收标准：**
- 仅帖子作者和管理员可删除
- 删除后返回剩余图片数量

---

### 4.3 评论模块

#### US-011：发表评论

| 字段 | 类型 | 约束 |
|------|------|------|
| 内容 | string | 必填，1-2000字符 |
| 父评论 ID | int | 选填，用于回复功能 |

**审核状态：**
- 普通用户评论默认 `status=pending`
- 管理员评论默认 `status=approved`

**验收标准：**
- 回复某条评论时，父评论必须属于同一帖子
- 评论创建成功后返回评论信息，含作者信息
- 未登录用户不能评论（返回 401）

---

#### US-012：查看评论列表

**验收标准：**
- 仅返回顶级评论（`parent_id` 为空）
- 仅显示审核通过的评论（`status=approved`）
- 按发布时间倒序排列
- 返回每条评论的作者信息
- 子评论通过 `parent_id` 关联（前端递归渲染）

---

#### US-013：删除评论

**验收标准：**
- 评论作者本人可删除
- 管理员可删除任意评论
- 删除父评论自动级联删除所有子评论

---

### 4.4 点赞模块

#### US-014：点赞/取消点赞

**验收标准：**
- Toggle 模式：已点赞则取消，未点赞则点赞
- 同一用户对同一帖子不能重复点赞（数据库 UNIQUE 约束）
- 返回当前点赞状态和最新点赞数
- 未登录用户不能点赞（返回 401）

---

### 4.5 收藏模块

#### US-015：收藏/取消收藏

**验收标准：**
- Toggle 模式：已收藏则取消，未收藏则收藏
- 同一用户对同一帖子不能重复收藏（数据库 UNIQUE 约束）
- 返回当前收藏状态和最新收藏数
- 未登录用户不能收藏（返回 401）

---

### 4.6 关注模块

#### US-016：关注/取关用户

**验收标准：**
- Toggle 模式：已关注则取关，未关注则关注
- 不能关注自己（返回 400）
- 目标用户不存在时返回 404
- 同一用户对同一用户不能重复关注（数据库 UNIQUE 约束）
- 返回操作后的关注状态、我的粉丝数、我的关注数

---

#### US-017：查看关注关系

**验收标准：**
- 返回 `is_following`（我是否关注了他）和 `is_followed_by`（他是否关注了我）
- 返回该用户的粉丝数和关注数
- 未登录时两人关系均返回 false

---

#### US-018：查看粉丝列表

**验收标准：**
- 支持分页，按关注时间倒序
- 返回粉丝用户信息（含粉丝数、关注数）

---

#### US-019：查看关注列表

**验收标准：**
- 支持分页，按关注时间倒序
- 返回被关注用户信息（含粉丝数、关注数）

---

#### US-020：查看互相关注好友

**验收标准：**
- 仅返回我关注且同时关注我的用户（双向关注）
- 支持分页

---

### 4.7 动态流模块（Feed）

#### US-021：获取关注用户动态

**验收标准：**
- 仅返回当前用户关注的所有用户发布的帖子
- 仅显示审核通过的帖子
- 按发布时间倒序
- 支持分页
- 需登录

---

### 4.8 私信模块

#### US-022：发起/获取会话

**验收标准：**
- 与目标用户已有会话则返回已有会话，不重复创建
- 不能给自己发私信（返回 400）

---

#### US-023：会话列表

**验收标准：**
- 按最新消息时间倒序
- 每条会话显示：对方用户信息、最后一条消息预览、未读消息数
- 需登录

---

#### US-024：发送消息

**验收标准：**
- 在指定会话中发送消息
- 发送后更新会话最新时间
- 需登录且必须是会话参与者

---

#### US-025：消息列表

**验收标准：**
- 分页，最新消息在前
- 需登录且必须是会话参与者

---

#### US-026：标记消息已读

**验收标准：**
- 将指定会话中所有对方发的未读消息标记为已读
- 返回实际标记的消息数量

---

#### US-027：未读消息总数

**验收标准：**
- 返回当前用户所有会话的未读消息总数

---

### 4.9 话题/标签模块

#### US-028：话题列表

**验收标准：**
- 按帖子数倒序排列
- 支持分页

---

#### US-029：搜索话题

**验收标准：**
- 按名称模糊匹配
- 最多返回 20 条

---

#### US-030：创建话题

**验收标准：**
- 话题名唯一，已存在则返回已有话题
- 需登录

---

#### US-031：为帖子设置标签

**验收标准：**
- 替换模式：先删后加
- 最多 9 个标签
- 仅帖子作者和管理员可操作
- 标签不存在则报错
- 设置后自动更新各标签的 `post_count`

---

#### US-032：获取帖子标签

**验收标准：**
- 返回帖子所有标签

---

#### US-033：移除帖子标签

**验收标准：**
- 仅帖子作者和管理员可操作
- 移除后自动减少标签的 `post_count`

---

#### US-034：话题下的帖子列表

**验收标准：**
- 支持分页
- 仅返回审核通过的已发布帖子

---

### 4.10 内容审核模块（管理员）

#### US-035：待审核帖子列表

**验收标准：**
- 仅管理员可访问
- 按创建时间升序（先到先审）
- 支持分页

---

#### US-036：已驳回帖子列表

**验收标准：**
- 按更新时间降序
- 支持分页

---

#### US-037：审核帖子

**验收标准：**
- `status` 只能为 `approved` 或 `rejected`
- 支持传入驳回原因

---

#### US-038：快捷通过/驳回帖子

**验收标准：**
- 单独提供 `approve` 和 `reject` 快捷接口

---

#### US-039：待审核评论列表

**验收标准：**
- 仅管理员可访问
- 支持分页

---

#### US-040：审核评论

**验收标准：**
- `status` 只能为 `approved` 或 `rejected`

---

#### US-041：快捷通过/驳回评论

---

## 五、API 接口文档

### 5.1 认证方式

- 采用 JWT（JSON Web Token）
- Token 类型：`Bearer`
- 有效期：默认 7 天（可配置）
- 传递方式：`Authorization: Bearer <token>`

### 5.2 公开接口（无需认证）

| 接口 | 说明 |
|------|------|
| `POST /auth/register` | 注册 |
| `POST /auth/login` | 登录 |
| `POST /auth/forgot-password` | 发起找回密码 |
| `GET /posts/` | 帖子列表 |
| `GET /posts/{id}` | 帖子详情 |
| `GET /posts/{id}/comments` | 评论列表 |
| `GET /posts/{id}/images` | 帖子图片列表 |
| `GET /users/{id}/follow/status` | 关注关系 |
| `GET /users/{id}/followers` | 粉丝列表 |
| `GET /users/{id}/following` | 关注列表 |
| `GET /tags/` | 话题列表 |
| `GET /tags/search` | 搜索话题 |
| `GET /tags/{id}/posts` | 话题下帖子 |
| `GET /tags/posts/{post_id}` | 帖子标签 |
| `GET /health` | 健康检查 |

### 5.3 需要认证的接口

| 接口 | 说明 |
|------|------|
| `POST /auth/reset-password` | 重置密码 |
| `GET /users/me` | 当前用户信息 |
| `POST /posts/` | 创建帖子 |
| `PUT /posts/{id}` | 更新帖子 |
| `DELETE /posts/{id}` | 删除帖子 |
| `POST /posts/{id}/comments` | 评论帖子 |
| `DELETE /posts/comments/{id}` | 删除评论 |
| `POST /posts/{id}/like` | 点赞/取消点赞 |
| `POST /posts/{id}/collect` | 收藏/取消收藏 |
| `POST /posts/{id}/images` | 上传图片 |
| `DELETE /posts/images/{id}` | 删除图片 |
| `POST /users/{id}/follow` | 关注/取关 |
| `GET /users/me/friends` | 互关好友列表 |
| `GET /feed/` | 动态流 |
| `POST /messages/conversations` | 发起/获取会话 |
| `GET /messages/conversations` | 会话列表 |
| `POST /messages/conversations/{id}/messages` | 发送消息 |
| `GET /messages/conversations/{id}/messages` | 消息列表 |
| `PUT /messages/conversations/{id}/read` | 标记已读 |
| `GET /messages/conversations/unread-count` | 未读总数 |
| `POST /tags/` | 创建话题 |
| `POST /tags/posts/{post_id}` | 设置帖子标签 |
| `DELETE /tags/posts/{post_id}/{tag_id}` | 移除帖子标签 |
| `GET /admin/posts/pending` | 待审核帖子 |
| `GET /admin/posts/rejected` | 已驳回帖子 |
| `POST /admin/posts/{id}/audit` | 审核帖子 |
| `POST /admin/posts/{id}/approve` | 快捷通过帖子 |
| `POST /admin/posts/{id}/reject` | 快捷驳回帖子 |
| `GET /admin/comments/pending` | 待审核评论 |
| `POST /admin/comments/{id}/audit` | 审核评论 |
| `POST /admin/comments/{id}/approve` | 快捷通过评论 |
| `POST /admin/comments/{id}/reject` | 快捷驳回评论 |

---

## 六、错误处理规范

| HTTP 状态码 | 场景 |
|-------------|------|
| 400 | 参数校验失败、不能关注自己、不能给自己发私信 |
| 401 | 未提供 Token / Token 无效或过期 |
| 403 | 无权限操作（不是作者、不是管理员） |
| 404 | 资源不存在（用户、帖子、评论、话题等） |
| 422 | Pydantic 请求体验证失败 |
| 500 | 服务器内部错误 |

错误响应格式：
```json
{ "detail": "具体错误信息" }
```

---

## 七、环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| SECRET_KEY | `your-super-secret-key-change-in-production` | JWT 签名密钥 |
| ALGORITHM | `HS256` | JWT 算法 |
| ACCESS_TOKEN_EXPIRE_MINUTES | `10080`（7天） | Token 有效期 |
| DATABASE_URL | `sqlite:///./fan_community.db` | 数据库连接 |
| UPLOAD_DIR | `uploads` | 图片存储目录 |
| MAX_IMAGE_SIZE | `5242880`（5MB） | 单张图片最大大小 |
| MAX_IMAGES_PER_POST | `9` | 单帖最多图片数 |
| CORS_ORIGINS | 空字符串 | CORS 允许的前端域名，生产环境必填 |

**CORS_ORIGINS 配置说明：**
- 开发环境：留空或设置 `http://localhost:3000,http://127.0.0.1:3000`
- 生产环境：`CORS_ORIGINS=https://your-frontend.com`，多个域名用逗号分隔

---

## 八、生产部署注意事项

1. **CORS**：`CORS_ORIGINS` 必须设置为具体前端域名，禁止使用 `*`
2. **SECRET_KEY**：不要使用默认密钥，设置随机字符串
3. **DATABASE_URL**：生产环境切换为 MySQL/PostgreSQL
4. **找回密码**：`/auth/forgot-password` 当前直接返回验证码，需接入邮件/短信服务
5. **静态文件**：当前使用 FastAPI StaticFiles Serve 本地文件，生产环境建议使用 Nginx 或 CDN
6. **超管权限**：`is_superuser=True` 的用户可删除任意帖子/评论、上传/删除任意图片、审核内容

---

*文档版本：v1.0.3 | 更新日期：2026-05-12*
