# 粉丝社群平台 - 项目功能说明文档

> **版本**: v1.0.66  
> **最后更新**: 2026-05-16  
> **文档说明**: 本文档详细说明项目所有功能模块、接口、数据模型和权限体系。每次修改项目时必须同步更新本文档。

---

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 核心架构](#2-核心架构)
- [3. 技术栈](#3-技术栈)
- [4. 权限体系](#4-权限体系)
- [5. 功能模块](#5-功能模块)
  - [5.1 认证模块](#51-认证模块)
  - [5.2 用户模块](#52-用户模块)
  - [5.3 关注模块](#53-关注模块)
  - [5.4 帖子模块](#54-帖子模块)
  - [5.5 明星模块](#55-明星模块)
  - [5.6 粉丝签到模块](#56-粉丝签到模块)
  - [5.7 风纪委员会模块](#57-风纪委员会模块)
  - [5.8 粉丝圈模块](#58-粉丝圈模块)
  - [5.9 粉丝牌模块](#59-粉丝牌模块)
  - [5.10 举报模块](#510-举报模块)
  - [5.11 私信模块](#511-私信模块)
  - [5.12 群聊模块](#512-群聊模块)
  - [5.13 话题/标签模块](#513-话题标签模块)
  - [5.14 内容审核模块](#514-内容审核模块)
  - [5.15 动态流模块](#515-动态流模块)
- [6. 数据模型](#6-数据模型)
- [7. 版本历史](#7-版本历史)

---

## 1. 项目概述

**粉丝社群平台**是一个以明星粉丝圈为核心的社交平台。项目由一个个明星所对应的粉丝圈构成，一个用户可以成为多个明星的粉丝。

### 核心功能

- 明星资料管理与关注
- 粉丝申请与审核（路人粉/真爱粉/死忠粉）
- 帖子发布与审核（仅粉丝可发帖）
- 粉丝每日签到打卡
- 粉丝牌/粉丝称号展示
- 风纪委员会自治审核
- 群聊与私信
- 举报与内容管理

---

## 2. 核心架构

```
粉丝社群平台
│
├── 粉丝圈 A（明星：张三）
│   ├── 粉丝（路人粉 / 真爱粉 / 死忠粉）
│   ├── 风纪委员会（member / chairman）
│   ├── 帖子板块
│   ├── 群聊
│   └── 每日签到
│
├── 粉丝圈 B（明星：李四）
│   └── ...
│
└── 粉丝圈 C（明星：王五）
    └── ...
```

### 关键规则

| 规则 | 说明 |
|------|------|
| 一个明星 | 对应一个粉丝圈（1:1） |
| 一个用户 | 可加入多个粉丝圈（N:M） |
| 粉丝圈 | 包含粉丝、风纪委、帖子、签到 |

### 用户加入粉丝圈流程

```
注册/登录 → 关注明星（即时） → 申请成为粉丝（需审核） → 审核通过 → 加入粉丝圈
                                                                    │
                                                    可选：申请风纪委员会（需审核）
                                                    可选：每日签到
                                                    可选：发帖（仅粉丝可发）
                                                    可选：设置粉丝牌展示
```

---

## 3. 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| ORM | SQLAlchemy |
| 数据库 | PostgreSQL |
| 认证 | JWT (OAuth2) |
| 文件存储 | 本地存储 |
| API 文档 | Swagger / ReDoc |

---

## 4. 权限体系

| 角色 | 发帖 | 签到 | 审核帖子 | 管理粉丝圈 | 关注 | 评论 | 点赞 | 收藏 | 举报 | 私信 | 群聊 |
|------|------|------|----------|------------|------|------|------|------|------|------|------|
| 游客 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 普通用户 | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 粉丝（已通过） | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 风纪委员 | ✅ | ✅ | ✅（本圈） | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 管理员 | ✅ | ✅ | ✅（全局） | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 粉丝类型

| 类型 | fan_type | 粉丝牌名称 | 粉丝牌颜色 |
|------|----------|------------|------------|
| 路人粉 | `casual` | {明星名}的路人粉 | #808080（灰色） |
| 真爱粉 | `true_fan` | {明星名}的真爱粉 | #FF69B4（粉色） |
| 死忠粉 | `diehard` | {明星名}的死忠粉 | #FFD700（金色） |

---

## 5. 功能模块

### 5.1 认证模块

**路由前缀**: `/auth`

| 接口 | 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|------|
| 用户注册 | POST | `/auth/register` | 注册账号（username/password 必填） | 公开 |
| 用户登录 | POST | `/auth/login` | 登录获取 JWT Token | 公开 |
| 找回密码 | POST | `/auth/forgot-password` | 生成验证码（开发环境返回明文） | 公开 |
| 重置密码 | POST | `/auth/reset-password` | 验证码重置密码（6位，15分钟有效） | 公开 |

---

### 5.2 用户模块

**路由前缀**: `/users`

| 接口 | 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|------|
| 用户公开资料 | GET | `/users/{user_id}` | 获取用户资料（含粉丝牌、帖子统计） | 公开 |
| 用户帖子（限制版） | GET | `/users/{user_id}/posts` | 获取用户帖子（支持数量和时间限制） | 公开 |
| 用户帖子（全部） | GET | `/users/{user_id}/posts/all` | 获取用户所有帖子 | 公开 |
| 用户在某明星的帖子 | GET | `/users/{user_id}/posts/by-star/{star_id}` | 按明星筛选用户帖子 | 公开 |
| 我的完整资料 | GET | `/users/me/profile` | 获取我的完整资料（含粉丝牌、统计数据） | 登录 |
| 获取我的资料 | GET | `/users/me` | 获取当前用户资料（含粉丝数/关注数） | 登录 |
| 编辑我的资料 | PATCH | `/users/me` | 编辑个人资料（nickname/avatar/bio/email/phone/political_status） | 登录（本人） |

#### 政治面貌

| 值 | 说明 |
|------|------|
| `masses` | 群众（默认） |
| `league` | 共青团员 |
| `party` | 中共党员 |

---

### 5.3 关注模块

**路由前缀**: `/users`

| 接口 | 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|------|
| 关注/取消关注 | POST | `/users/{user_id}/follow` | 关注或取消关注用户 | 登录 |
| 关注状态 | GET | `/users/{user_id}/follow/status` | 获取关注关系 | 登录 |
| 粉丝列表 | GET | `/users/{user_id}/followers` | 获取用户粉丝列表 | 公开 |
| 关注列表 | GET | `/users/{user_id}/following` | 获取用户关注列表 | 公开 |
| 好友列表 | GET | `/users/me/friends` | 获取互相关注的好友列表 | 登录 |

---

### 5.4 帖子模块

**路由前缀**: `/posts`

| 接口 | 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|------|
| 创建帖子 | POST | `/posts/` | 创建帖子（需关联明星，仅粉丝可发） | 登录（粉丝/管理员） |
| 帖子列表 | GET | `/posts/` | 获取帖子列表（置顶优先，分页） | 公开 |
| 帖子详情 | GET | `/posts/{post_id}` | 获取帖子详情 | 公开 |
| 更新帖子 | PUT | `/posts/{post_id}` | 更新帖子 | 登录（仅作者） |
| 删除帖子 | DELETE | `/posts/{post_id}` | 删除帖子 | 登录（作者/管理员） |
| 评论帖子 | POST | `/posts/{post_id}/comments` | 评论帖子（支持回复） | 登录 |
| 评论列表 | GET | `/posts/{post_id}/comments` | 获取帖子评论列表 | 公开 |
| 删除评论 | DELETE | `/posts/comments/{comment_id}` | 删除评论 | 登录（作者/管理员） |
| 评论点赞 | POST | `/posts/comments/{comment_id}/like` | 评论点赞/取消 | 登录 |
| 帖子点赞 | POST | `/posts/{post_id}/like` | 帖子点赞/取消 | 登录 |
| 上传图片 | POST | `/posts/{post_id}/images` | 上传帖子图片（最多9张，5MB/张） | 登录（作者/管理员） |
| 获取图片 | GET | `/posts/{post_id}/images` | 获取帖子图片 | 公开 |
| 删除图片 | DELETE | `/posts/images/{image_id}` | 删除帖子图片 | 登录（作者/管理员） |
| 上传视频 | POST | `/posts/{post_id}/videos` | 上传视频（100MB/5分钟） | 登录（作者/管理员） |
| 获取视频 | GET | `/posts/{post_id}/videos` | 获取帖子视频 | 公开 |
| 删除视频 | DELETE | `/posts/videos/{video_id}` | 删除视频 | 登录（作者/管理员） |
| 更新封面 | PATCH | `/posts/videos/{video_id}/thumbnail` | 更新视频封面 | 登录（作者/管理员） |
| 收藏/取消 | POST | `/posts/{post_id}/collect` | 收藏/取消收藏 | 登录 |
| 热门推荐 | GET | `/posts/recommended` | 基于热度算法推荐帖子 | 公开 |
| 置顶/取消 | POST | `/posts/{post_id}/pin` | 置顶/取消置顶 | 登录（管理员） |
| 加精/取消 | POST | `/posts/{post_id}/feature` | 加精/取消加精 | 登录（管理员） |
| 加精列表 | GET | `/posts/featured` | 获取加精帖子列表 | 公开 |

#### 热度算法

```
热度分数 = (浏览量×1 + 点赞数×5 + 评论数×10 + 收藏数×8) / 发布小时数^1.5
```

| 维度 | 权重 | 说明 |
|------|------|------|
| 浏览量 | ×1 | 基础互动 |
| 点赞数 | ×5 | 中度互动 |
| 收藏数 | ×8 | 较高认可 |
| 评论数 | ×10 | 深度互动 |

---

### 5.5 明星模块

**路由前缀**: `/stars`

| 接口 | 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|------|
| 创建明星 | POST | `/stars/` | 创建明星资料 | 登录（管理员） |
| 明星列表 | GET | `/stars/` | 获取明星列表（支持搜索） | 公开 |
| 明星详情 | GET | `/stars/{star_id}` | 获取明星详情 | 公开 |
| 更新明星 | PUT | `/stars/{star_id}` | 更新明星资料 | 登录（管理员） |
| 删除明星 | DELETE | `/stars/{star_id}` | 删除明星（软删除） | 登录（管理员） |
| 明星发帖 | POST | `/stars/{star_id}/posts` | 在明星板块发帖 | 登录（粉丝/管理员） |
| 明星帖子列表 | GET | `/stars/{star_id}/posts` | 获取明星帖子列表 | 公开 |
| 粉丝数排行 | GET | `/stars/ranking/fans` | 明星粉丝数排行榜 | 公开 |
| 热度排行 | GET | `/stars/ranking/heat` | 明星热度排行榜 | 公开 |
| 帖子数排行 | GET | `/stars/ranking/posts` | 明星帖子数排行榜 | 公开 |
| 申请粉丝 | POST | `/stars/{star_id}/fans/apply` | 申请成为粉丝 | 登录 |
| 待审核粉丝 | GET | `/stars/{star_id}/fans/pending` | 获取待审核粉丝列表 | 登录（管理员） |
| 审核粉丝 | POST | `/stars/{star_id}/fans/{fan_id}/review` | 审核粉丝申请（自动创建粉丝牌） | 登录（管理员） |
| 粉丝列表 | GET | `/stars/{star_id}/fans` | 获取明星粉丝列表 | 公开 |
| 我的粉丝申请 | GET | `/stars/users/me/fan-applications` | 获取我的粉丝申请 | 登录 |
| 退出粉丝 | DELETE | `/stars/{star_id}/fans/me` | 取消申请或退出粉丝 | 登录（本人） |
| 修改粉丝类型 | PATCH | `/stars/{star_id}/fans/{fan_id}/type` | 升级/修改粉丝类型 | 登录（管理员） |
| 关注明星 | POST | `/stars/{star_id}/follow` | 关注/取消关注明星 | 登录 |
| 明星关注者 | GET | `/stars/{star_id}/followers` | 获取明星关注者列表 | 公开 |
| 关注状态 | GET | `/stars/{star_id}/follow/status` | 检查是否关注 | 登录 |
| 我关注的明星 | GET | `/stars/users/me/following` | 获取我关注的明星列表 | 登录 |

---

### 5.6 粉丝签到模块

**路由前缀**: `/stars`

签到时间窗口：**当日 04:00 至次日 04:00**

| 时间段 | 归属日期 |
|--------|----------|
| 04:00 - 23:59:59 | 当天 |
| 00:00 - 03:59:59 | 前一天 |

| 接口 | 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|------|
| 每日签到 | POST | `/stars/{star_id}/checkin` | 签到打卡 | 登录（粉丝） |
| 签到统计 | GET | `/stars/{star_id}/checkin/status` | 我的签到统计 | 登录（粉丝） |
| 签到日历 | GET | `/stars/{star_id}/checkin/calendar` | 某月已签到日期 | 登录（粉丝） |
| 签到排行榜 | GET | `/stars/{star_id}/checkin/rank` | 签到排行榜 | 公开 |
| 签到历史 | GET | `/stars/{star_id}/checkin/history` | 我的签到历史 | 登录（粉丝） |

#### 连续签到奖励

| 连续天数 | 积分 |
|----------|------|
| 1-2 天 | 1 分 |
| 3-6 天 | 2 分 |
| 7-29 天 | 3 分 |
| 30+ 天 | 5 分 |

---

### 5.7 风纪委员会模块

**路由前缀**: `/stars`

| 接口 | 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|------|
| 申请加入 | POST | `/stars/{star_id}/committee/apply` | 申请加入风纪委员会 | 登录（粉丝） |
| 待审核申请 | GET | `/stars/{star_id}/committee/pending` | 获取待审核申请 | 登录（管理员/委员长） |
| 审核申请 | POST | `/stars/{star_id}/committee/{app_id}/review` | 审核风纪委员会申请 | 登录（管理员/委员长） |
| 成员列表 | GET | `/stars/{star_id}/committee` | 获取风纪委员会成员列表 | 公开 |
| 我的申请 | GET | `/stars/users/me/committee-applications` | 获取我的风纪委员会申请 | 登录 |
| 辞去职务 | DELETE | `/stars/{star_id}/committee/me` | 辞去风纪委员会职务 | 登录（本人） |
| 审核帖子 | POST | `/stars/{star_id}/committee/posts/{post_id}/audit` | 风纪委员审核帖子 | 登录（风纪委员） |
| 待审核帖子 | GET | `/stars/{star_id}/committee/posts/pending` | 获取待审核帖子列表 | 登录（风纪委员） |

---

### 5.8 粉丝圈模块

**路由前缀**: `/fan-circles`

| 接口 | 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|------|
| 粉丝圈列表 | GET | `/fan-circles/` | 获取所有粉丝圈 | 公开 |
| 粉丝圈详情 | GET | `/fan-circles/{circle_id}` | 获取粉丝圈详情 | 公开 |
| 通过明星获取 | GET | `/fan-circles/by-star/{star_id}` | 通过明星ID获取（自动创建） | 公开 |
| 更新粉丝圈 | PUT | `/fan-circles/{circle_id}` | 修改粉丝圈信息 | 登录（管理员） |
| 成员列表 | GET | `/fan-circles/{circle_id}/members` | 获取成员列表（可按类型筛选） | 公开 |
| 成员统计 | GET | `/fan-circles/{circle_id}/members/count` | 按粉丝类型统计 | 公开 |
| 完整概览 | GET | `/fan-circles/{circle_id}/overview` | 粉丝圈完整数据 | 公开 |
| 我加入的 | GET | `/fan-circles/users/me/joined` | 我加入的粉丝圈（含签到状态） | 登录 |
| 粉丝总览 | GET | `/fan-circles/users/me/summary` | 我的粉丝总览 | 登录 |

---

### 5.9 粉丝牌模块

**路由前缀**: `/fan-badges`

| 接口 | 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|------|
| 我的粉丝牌 | GET | `/fan-badges/my` | 获取我的所有粉丝牌 | 登录 |
| 当前展示的 | GET | `/fan-badges/my/displayed` | 获取正在展示的粉丝牌 | 登录 |
| 设置展示 | POST | `/fan-badges/my/display` | 设置展示的粉丝牌（每人最多1个） | 登录 |
| 取消展示 | DELETE | `/fan-badges/my/display` | 取消展示粉丝牌 | 登录 |
| 查看他人展示的 | GET | `/fan-badges/user/{user_id}` | 查看用户展示的粉丝牌 | 公开 |
| 查看他人所有 | GET | `/fan-badges/user/{user_id}/all` | 查看用户所有粉丝牌 | 公开 |
| 粉丝牌配置 | GET | `/fan-badges/config` | 获取称号、颜色配置 | 公开 |

---

### 5.10 粉丝圈共同空间模块

**路由前缀**: `/fan-circles`

| 接口 | 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|------|
| 上传照片 | POST | `/fan-circles/{circle_id}/photos` | 上传照片到共同空间 | 登录（粉丝） |
| 已审核照片列表 | GET | `/fan-circles/{circle_id}/photos` | 获取已审核通过的照片 | 公开 |
| 所有照片列表 | GET | `/fan-circles/{circle_id}/photos/all` | 获取所有照片（含待审核） | 登录（管理员） |
| 我上传的照片 | GET | `/fan-circles/{circle_id}/photos/my` | 获取我上传的照片 | 登录（粉丝） |
| 待审核照片 | GET | `/fan-circles/{circle_id}/photos/pending` | 获取待审核照片列表 | 登录（管理员） |
| 审核照片 | POST | `/fan-circles/{circle_id}/photos/{photo_id}/audit` | 审核照片（通过/驳回） | 登录（管理员） |
| 快捷通过 | POST | `/fan-circles/{circle_id}/photos/{photo_id}/approve` | 快捷通过照片 | 登录（管理员） |
| 快捷驳回 | POST | `/fan-circles/{circle_id}/photos/{photo_id}/reject` | 快捷驳回照片 | 登录（管理员） |
| 删除照片 | DELETE | `/fan-circles/{circle_id}/photos/{photo_id}` | 删除照片 | 登录（上传者/管理员） |

#### 照片上传限制

- 支持格式：jpeg/png/gif/webp
- 单文件最大：5MB
- 照片状态：pending（待审核）/ approved（已通过）/ rejected（已驳回）

---

### 5.11 举报模块

**路由前缀**: `/reports`

| 接口 | 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|------|
| 举报原因列表 | GET | `/reports/reasons` | 获取举报原因分类 | 公开 |
| 提交举报 | POST | `/reports/` | 举报帖子 | 登录 |
| 我的举报 | GET | `/reports/my` | 获取我的举报记录 | 登录 |
| 举报列表 | GET | `/reports/` | 获取举报列表（管理员） | 登录（管理员） |
| 举报统计 | GET | `/reports/stats` | 举报统计数据 | 登录（管理员） |
| 举报详情 | GET | `/reports/{report_id}` | 获取举报详情 | 登录（举报人/管理员） |
| 处理举报 | POST | `/reports/{report_id}/handle` | 处理举报（成立时自动驳回帖子） | 登录（管理员） |

#### 举报原因

`垃圾广告` | `色情低俗` | `虚假信息` | `人身攻击` | `侵犯版权` | `违法违规` | `恶意刷屏` | `其他`

---

### 5.12 私信模块

**路由前缀**: `/messages`

| 接口 | 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|------|
| 发起/获取会话 | POST | `/messages/conversations` | 获取或创建私信会话 | 登录 |
| 会话列表 | GET | `/messages/conversations` | 获取我的会话列表（含未读数） | 登录 |
| 发送消息 | POST | `/messages/conversations/{conv_id}/messages` | 发送私信（支持 text/image/sticker/location） | 登录（参与者） |
| 消息列表 | GET | `/messages/conversations/{conv_id}/messages` | 获取会话消息 | 登录（参与者） |

#### 消息类型

| 类型 | 说明 |
|------|------|
| `text` | 文本消息 |
| `image` | 图片消息 |
| `sticker` | 表情包消息 |
| `location` | 位置消息（含经纬度、名称、地址） |
| 标记已读 | PUT | `/messages/conversations/{conv_id}/read` | 标记消息已读 | 登录（参与者） |
| 未读总数 | GET | `/messages/conversations/unread-count` | 获取未读消息总数 | 登录 |

---

### 5.13 群聊模块

**路由前缀**: `/groups`

| 接口 | 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|------|
| 创建群聊 | POST | `/groups/` | 创建群聊（创建者自动成为群主） | 登录 |
| 我的群聊 | GET | `/groups/` | 获取我加入的群聊列表 | 登录 |
| 群聊详情 | GET | `/groups/{group_id}` | 获取群聊详情 | 登录（群成员） |
| 更新群聊 | PUT | `/groups/{group_id}` | 更新群聊信息 | 登录（群主/管理员） |
| 解散群聊 | DELETE | `/groups/{group_id}` | 解散群聊 | 登录（仅群主） |
| 成员列表 | GET | `/groups/{group_id}/members` | 获取群成员列表 | 登录（群成员） |
| 邀请成员 | POST | `/groups/{group_id}/invite` | 邀请用户加入 | 登录（群主/管理员） |
| 加入群聊 | POST | `/groups/{group_id}/join` | 加入群聊 | 登录 |
| 退出群聊 | POST | `/groups/{group_id}/leave` | 退出群聊 | 登录 |
| 移除成员 | DELETE | `/groups/{group_id}/members/{user_id}` | 移除群成员 | 登录（群主/管理员） |
| 设置角色 | PATCH | `/groups/{group_id}/members/{user_id}/role` | 设置成员角色 | 登录（仅群主） |
| 群消息列表 | GET | `/groups/{group_id}/messages` | 获取群聊消息 | 登录（群成员） |
| 发送群消息 | POST | `/groups/{group_id}/messages` | 发送群消息（text/image/sticker/location/system） | 登录（群成员） |

---

### 5.14 话题/标签模块

**路由前缀**: `/tags`

| 接口 | 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|------|
| 话题列表 | GET | `/tags/` | 获取话题列表（按帖子数排序） | 公开 |
| 搜索话题 | GET | `/tags/search` | 搜索话题（模糊匹配） | 公开 |
| 创建话题 | POST | `/tags/` | 创建新话题 | 登录 |
| 设置标签 | POST | `/tags/posts/{post_id}` | 为帖子设置标签（最多9个） | 登录（作者/管理员） |
| 获取标签 | GET | `/tags/posts/{post_id}` | 获取帖子标签 | 公开 |
| 移除标签 | DELETE | `/tags/posts/{post_id}/{tag_id}` | 从帖子移除标签 | 登录（作者/管理员） |
| 话题帖子 | GET | `/tags/{tag_id}/posts` | 获取话题下的帖子列表 | 公开 |

---

### 5.15 内容审核模块

**路由前缀**: `/admin`

| 接口 | 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|------|
| 待审核帖子 | GET | `/admin/posts/pending` | 获取待审核帖子列表 | 登录（管理员） |
| 已驳回帖子 | GET | `/admin/posts/rejected` | 获取已驳回帖子列表 | 登录（管理员） |
| 审核帖子 | POST | `/admin/posts/{post_id}/audit` | 审核帖子（通过/驳回） | 登录（管理员） |
| 快捷通过 | POST | `/admin/posts/{post_id}/approve` | 快捷通过帖子 | 登录（管理员） |
| 快捷驳回 | POST | `/admin/posts/{post_id}/reject` | 快捷驳回帖子 | 登录（管理员） |
| 待审核评论 | GET | `/admin/comments/pending` | 获取待审核评论列表 | 登录（管理员） |
| 审核评论 | POST | `/admin/comments/{comment_id}/audit` | 审核评论 | 登录（管理员） |
| 快捷通过评论 | POST | `/admin/comments/{comment_id}/approve` | 快捷通过评论 | 登录（管理员） |
| 快捷驳回评论 | POST | `/admin/comments/{comment_id}/reject` | 快捷驳回评论 | 登录（管理员） |

---

### 5.16 动态流模块

**路由前缀**: `/feed`

| 接口 | 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|------|
| 动态流 | GET | `/feed/` | 获取关注用户的帖子动态 | 登录 |

---

### 5.17 表情包模块

**路由前缀**: `/stickers`

| 接口 | 方法 | 路径 | 功能 | 权限 |
|------|------|------|------|------|
| 上传表情包 | POST | `/stickers/` | 上传表情包（gif/webp/png，2MB） | 登录 |
| 表情包列表 | GET | `/stickers/` | 获取公开表情包列表 | 公开 |
| 搜索表情包 | GET | `/stickers/search` | 按名称搜索表情包 | 公开 |
| 分类列表 | GET | `/stickers/categories` | 获取表情包分类 | 公开 |
| 删除表情包 | DELETE | `/stickers/{sticker_id}` | 删除表情包 | 登录（上传者/管理员） |
| 我的收藏 | GET | `/stickers/my` | 获取我的表情包收藏 | 登录 |
| 收藏表情包 | POST | `/stickers/my/{sticker_id}` | 收藏表情包（上限100个） | 登录 |
| 移除收藏 | DELETE | `/stickers/my/{sticker_id}` | 从收藏中移除 | 登录 |
| 收藏数量 | GET | `/stickers/my/count` | 获取收藏数量 | 登录 |

#### 表情包使用说明

- 在群聊和私信中，消息类型支持 `sticker`，发送时携带 `sticker_id`
- 用户最多收藏 **100** 个表情包
- 公开表情包所有用户可见和使用
- 表情包分类：`default`（默认）/ `emoji`（表情）/ `custom`（自定义）

---

## 6. 数据模型

| 模型 | 表名 | 说明 |
|------|------|------|
| User | users | 用户表 |
| Post | posts | 帖子表 |
| Comment | comments | 评论表 |
| Like | likes | 帖子点赞表 |
| CommentLike | comment_likes | 评论点赞表 |
| Collection | collections | 收藏表 |
| Follow | follows | 用户关注关系表 |
| VerificationCode | verification_codes | 验证码表 |
| PostImage | post_images | 帖子图片表 |
| PostVideo | post_videos | 帖子视频表 |
| Conversation | conversations | 私信会话表 |
| Message | messages | 私信消息表 |
| GroupChat | group_chats | 群聊表 |
| GroupMember | group_members | 群成员表 |
| GroupMessage | group_messages | 群聊消息表 |
| Star | stars | 明星资料表 |
| StarPost | star_posts | 明星帖子关联表 |
| StarFollow | star_follows | 明星关注关联表 |
| StarFan | star_fans | 粉丝申请表 |
| FanCheckIn | fan_checkins | 粉丝签到表 |
| DisciplineCommittee | discipline_committees | 风纪委员会表 |
| Report | reports | 举报表 |
| FanCircle | fan_circles | 粉丝圈表 |
| FanBadge | fan_badges | 粉丝牌表 |
| FanCirclePhoto | fan_circle_photos | 粉丝圈共同空间照片表 |
| Sticker | stickers | 表情包表 |
| UserSticker | user_stickers | 用户表情包收藏表 |
| Tag | tags | 话题/标签表 |
| PostTag | post_tags | 帖子-话题关联表 |
| Location | locations | 位置信息表 |

-------

## 7. 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.50 | 2026-05-14 | 新增举报功能 |
| v1.0.51 | 2026-05-14 | 限制仅粉丝可发帖 |
| v1.0.52 | 2026-05-14 | 定义粉丝类型（路人粉/真爱粉/死忠粉） |
| v1.0.53 | 2026-05-14 | 新增粉丝每日签到打卡 |
| v1.0.54 | 2026-05-15 | 修复明星板块发帖缺少粉丝验证 |
| v1.0.55 | 2026-05-15 | 新增帖子置顶和加精功能 |
| v1.0.56 | 2026-05-15 | 新增基于热度的帖子推荐 |
| v1.0.57 | 2026-05-15 | 新增粉丝圈功能 |
| v1.0.58 | 2026-05-15 | 明确项目架构，优化粉丝圈接口 |
| v1.0.59 | 2026-05-15 | 新增粉丝牌/粉丝称号系统 |
| v1.0.60 | 2026-05-15 | 新增用户个人主页帖子展示 |
| v1.0.61 | 2026-05-16 | 创建项目功能说明文档 |
| v1.0.62 | 2026-05-16 | 用户新增政治面貌字段 |
| v1.0.63 | 2026-05-16 | 粉丝圈新增共同空间照片功能 |
| v1.0.64 | 2026-05-16 | 新增表情包功能 |
| v1.0.65 | 2026-05-16 | 聊天新增定位功能 |
| v1.0.66 | 2026-05-20 | 代码审计修复（安全+质量） |

-------

**文档维护说明**: 每次修改项目时，必须同步更新本文档中对应的功能模块、接口列表和数据模型部分。
