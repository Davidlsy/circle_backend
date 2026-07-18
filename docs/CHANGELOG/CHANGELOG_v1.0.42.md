# 更新日志 v1.0.42

## 版本信息
- **版本号**: v1.0.42
- **发布日期**: 2026-05-14
- **更新类型**: 功能新增

## 更新概述

本次更新让帖子内容支持 **Markdown 格式**。用户发布帖子时可使用 Markdown 语法编写内容，API 返回渲染后的 HTML 和纯文本摘要。

---

## 新增功能

### 1. Markdown 渲染

#### 1.1 支持的 Markdown 语法

| 语法 | 效果 | 示例 |
|------|------|------|
| 标题 | h1-h6 | `# 标题` |
| 加粗 | **粗体** | `**粗体**` |
| 斜体 | *斜体* | `*斜体*` |
| 删除线 | ~~删除~~ | `~~删除~~` |
| 链接 | 可点击链接 | `[文字](url)` |
| 图片 | 嵌入图片 | `![描述](url)` |
| 代码 | 行内代码 | `` `代码` `` |
| 代码块 | 代码高亮 | ` ```代码块``` ` |
| 引用 | 引用块 | `> 引用` |
| 列表 | 有序/无序 | `- 列表项` |
| 表格 | 表格 | `\| 表头 \|` |
| 分隔线 | 水平线 | `---` |

#### 1.2 API 返回字段变化

帖子列表和详情接口新增两个字段：

```json
{
  "id": 123,
  "title": "帖子标题",
  "content": "## Markdown 内容\n\n**加粗**和*斜体*",
  "content_html": "<h2>Markdown 内容</h2>\n<p><strong>加粗</strong>和<em>斜体</em></p>",
  "content_summary": "Markdown 内容 加粗和斜体",
  ...
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `content` | string | 原始 Markdown 内容（不变） |
| `content_html` | string | 渲染后的安全 HTML（新增） |
| `content_summary` | string | 纯文本摘要，最多 200 字（新增） |

#### 1.3 安全特性

| 特性 | 说明 |
|------|------|
| XSS 防护 | 使用 bleach 清理 HTML，移除危险标签 |
| 标签白名单 | 仅允许安全的 HTML 标签 |
| 属性白名单 | 仅允许安全的 HTML 属性 |
| 协议白名单 | 仅允许 http/https 协议的链接 |
| 代码安全 | 禁止在 Markdown 中嵌入 HTML 属性 |

允许的 HTML 标签：`p, br, hr, h1-h6, strong, em, b, i, u, s, del, ins, a, ul, ol, li, blockquote, pre, code, table, thead, tbody, tr, th, td, img, div, span, sup, sub`

---

### 2. Markdown 工具模块

新增 `app/utils/markdown_utils.py`，提供以下函数：

| 函数 | 功能 |
|------|------|
| `render_markdown(text)` | 将 Markdown 渲染为安全的 HTML |
| `strip_markdown(text, max_length)` | 去除 Markdown 语法，返回纯文本摘要 |

**实现方式**:
- 使用 `markdown` 库渲染（支持 extra、codehilite、toc 等扩展）
- 使用 `bleach` 库清理 HTML（防止 XSS）
- 库不可用时自动降级为纯文本

---

## 文件变更

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `app/utils/markdown_utils.py` | Markdown 渲染和 HTML 安全清理工具 |

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/schemas.py` | PostPublic 新增 content_html、content_summary 字段 |
| `app/routers/post_router.py` | 帖子列表和详情返回渲染后的 HTML 和摘要 |
| `app/main.py` | 更新版本号至 1.0.42 |

---

## 依赖安装

```bash
pip install markdown bleach
```

- `markdown`: Markdown 渲染引擎
- `bleach`: HTML 清理，防止 XSS 攻击

---

## 使用示例

### 发布 Markdown 帖子

```bash
curl -X POST "http://localhost:8000/posts/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "使用 Markdown 写帖子",
    "content": "## 简介\n\n这是一篇 **Markdown** 格式的帖子。\n\n- 支持列表\n- 支持表格\n- 支持 `代码`\n\n```python\nprint(\"Hello World\")\n```"
  }'
```

### API 返回

```json
{
  "id": 123,
  "title": "使用 Markdown 写帖子",
  "content": "## 简介\n\n这是一篇 **Markdown** 格式的帖子。\n\n- 支持列表\n- 支持表格\n- 支持 `代码`\n\n```python\nprint(\"Hello World\")\n```",
  "content_html": "<h2>简介</h2>\n<p>这是一篇 <strong>Markdown</strong> 格式的帖子。</p>\n<ul>\n<li>支持列表</li>\n<li>支持表格</li>\n<li>支持 <code>代码</code></li>\n</ul>\n<pre><code class=\"language-python\">print(\"Hello World\")\n</code></pre>",
  "content_summary": "简介 这是一篇 Markdown 格式的帖子。 支持列表 支持表格 支持 代码...",
  ...
}
```

---

## 向后兼容

- `content` 字段保持不变，仍返回原始 Markdown 文本
- 新增的 `content_html` 和 `content_summary` 字段有默认值
- 现有纯文本帖子不受影响（纯文本会被包裹在 `<p>` 标签中）

---

## 验证清单

- [x] Markdown 渲染工具函数
- [x] HTML 安全清理（XSS 防护）
- [x] 帖子列表返回 content_html
- [x] 帖子详情返回 content_html
- [x] 纯文本摘要生成
- [x] 库不可用时自动降级
- [x] 向后兼容
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
