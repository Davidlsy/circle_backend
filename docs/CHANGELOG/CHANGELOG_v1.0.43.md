# 更新日志 v1.0.43

## 版本信息
- **版本号**: v1.0.43
- **发布日期**: 2026-05-14
- **更新类型**: 功能新增

## 更新概述

本次更新让帖子支持 **HTML 格式**内容。用户发布帖子时可选择三种内容格式：**Markdown**、**HTML** 或**纯文本**，系统自动渲染为安全的 HTML 返回。

---

## 新增功能

### 1. 多格式内容支持

#### 1.1 支持的内容格式

| 格式 | content_format 值 | 说明 |
|------|-------------------|------|
| Markdown | `markdown`（默认） | 支持标题、加粗、代码块、表格等语法 |
| HTML | `html` | 支持直接编写 HTML 标签 |
| 纯文本 | `plain` | 纯文本，自动转义 HTML 特殊字符 |

#### 1.2 API 请求变化

**创建帖子**：
```json
{
  "title": "帖子标题",
  "content": "<h1>HTML 标题</h1><p>一段 <strong>HTML</strong> 内容</p>",
  "content_format": "html",
  "is_published": true
}
```

**更新帖子**：
```json
{
  "content": "更新后的内容",
  "content_format": "plain"
}
```

#### 1.3 API 返回变化

```json
{
  "id": 123,
  "title": "帖子标题",
  "content": "<h1>HTML 标题</h1><p>一段内容</p>",
  "content_format": "html",
  "content_html": "<h1>HTML 标题</h1><p>一段内容</p>",
  "content_summary": "HTML 标题 一段内容",
  ...
}
```

| 字段 | 说明 |
|------|------|
| `content` | 原始内容（不变） |
| `content_format` | 内容格式：`markdown` / `html` / `plain`（新增） |
| `content_html` | 渲染后的安全 HTML |
| `content_summary` | 纯文本摘要 |

---

### 2. HTML 安全清理

用户提交的 HTML 内容会经过安全清理，防止 XSS 攻击：

| 安全措施 | 说明 |
|----------|------|
| 标签白名单 | 仅允许安全的 HTML 标签 |
| 属性白名单 | 仅允许安全的 HTML 属性 |
| 协议白名单 | 仅允许 http/https 协议 |
| Script 移除 | 自动移除 `<script>` 标签 |
| 事件移除 | 自动移除 `onclick` 等事件属性 |

**允许的 HTML 标签**：
`p, br, hr, h1-h6, strong, em, b, i, u, s, del, ins, a, ul, ol, li, blockquote, pre, code, table, thead, tbody, tr, th, td, img, div, span, sup, sub`

---

### 3. 各格式渲染行为

| 格式 | 渲染行为 |
|------|----------|
| `markdown` | Markdown → HTML（使用 markdown 库）→ 安全清理（使用 bleach） |
| `html` | HTML → 安全清理（使用 bleach） |
| `plain` | 纯文本 → HTML 转义 → 包裹 `<p>` 标签 |

---

### 4. 数据模型变更

Post 模型新增字段：

```python
content_format = Column(String(20), default="markdown", nullable=False)
# 可选值：markdown / html / plain
```

---

## 文件变更

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/models.py` | Post 模型新增 content_format 字段 |
| `app/schemas.py` | PostBase/PostCreate/PostUpdate/PostPublic 新增 content_format |
| `app/utils/markdown_utils.py` | 新增 sanitize_html()、render_content()、generate_summary() |
| `app/routers/post_router.py` | 帖子列表/详情根据格式渲染内容 |
| `app/main.py` | 更新版本号至 1.0.43 |

---

## 数据库迁移

```bash
alembic revision --autogenerate -m "add_content_format_to_posts"
alembic upgrade head
```

**变更内容**：
- posts 表新增 `content_format` 字段（VARCHAR(20)，默认 `markdown`）

---

## 使用示例

### Markdown 格式（默认）
```bash
curl -X POST "http://localhost:8000/posts/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Markdown 帖子", "content": "## 标题\n**加粗**", "content_format": "markdown"}'
```

### HTML 格式
```bash
curl -X POST "http://localhost:8000/posts/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "HTML 帖子", "content": "<h2>标题</h2><p><strong>加粗</strong></p>", "content_format": "html"}'
```

### 纯文本格式
```bash
curl -X POST "http://localhost:8000/posts/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "纯文本帖子", "content": "这是一段纯文本", "content_format": "plain"}'
```

---

## 向后兼容

- `content_format` 默认值为 `markdown`，现有帖子不受影响
- 未传 `content_format` 时自动使用 Markdown 格式
- `content_html` 和 `content_summary` 字段保持不变

---

## 验证清单

- [x] Post 模型新增 content_format 字段
- [x] Schema 添加格式选择和正则验证
- [x] HTML 格式安全清理（XSS 防护）
- [x] 纯文本格式 HTML 转义
- [x] Markdown 格式渲染（保持不变）
- [x] 统一渲染函数 render_content()
- [x] 统一摘要函数 generate_summary()
- [x] 帖子列表根据格式渲染
- [x] 帖子详情根据格式渲染
- [x] 向后兼容
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
