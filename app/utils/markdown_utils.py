"""
内容渲染工具

支持 Markdown、HTML、纯文本三种格式，统一渲染为安全的 HTML。
"""
import re
import html as html_module
from typing import Optional

from app.logging_config import logger

# 尝试导入 markdown 库
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    logger.warning("markdown 库未安装，Markdown 渲染功能不可用。请运行: pip install markdown")

# 尝试导入 bleach 用于 HTML 清理
try:
    import bleach
    BLEACH_AVAILABLE = True
except ImportError:
    BLEACH_AVAILABLE = False
    logger.warning("bleach 库未安装，HTML 清理功能受限。请运行: pip install bleach")


# 允许的 HTML 标签（用于 bleach 清理）
ALLOWED_TAGS = [
    "p", "br", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "em", "b", "i", "u", "s", "del", "ins",
    "a",
    "ul", "ol", "li",
    "blockquote",
    "pre", "code",
    "table", "thead", "tbody", "tr", "th", "td",
    "img",
    "div", "span",
    "sup", "sub",
]

# 允许的属性
ALLOWED_ATTRIBUTES = {
    "*": ["class", "id"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "code": ["class"],
    "pre": ["class"],
}

# 允许的协议
ALLOWED_PROTOCOLS = ["http", "https", "mailto", "#"]


def render_markdown(text: str) -> str:
    """
    将 Markdown 文本渲染为安全的 HTML

    Args:
        text: Markdown 格式的文本

    Returns:
        str: 渲染后的安全 HTML
    """
    if not text:
        return ""

    if not MARKDOWN_AVAILABLE:
        # markdown 库不可用时，返回转义后的纯文本
        import html
        return f"<p>{html.escape(text)}</p>"

    # 使用 markdown 库渲染
    md = markdown.Markdown(
        extensions=[
            "extra",          # 支持表格、脚注等扩展语法
            "codehilite",     # 代码高亮
            "toc",            # 目录生成
            "nl2br",          # 换行转 <br>
            "sane_lists",     # 更合理的列表解析
        ],
        enable_attributes=False,  # 禁止在 Markdown 中使用 HTML 属性
    )

    raw_html = md.convert(text)
    md.reset()  # 重置实例状态

    # 使用 bleach 清理 HTML，防止 XSS
    if BLEACH_AVAILABLE:
        clean_html = bleach.clean(
            raw_html,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            protocols=ALLOWED_PROTOCOLS,
            strip=True,  # 移除不允许的标签（而非转义）
        )
    else:
        # bleach 不可用时，使用正则移除危险标签作为兜底
        clean_html = re.sub(r'<script[^>]*>.*?</script>', '', raw_html, flags=re.DOTALL | re.IGNORECASE)
        clean_html = re.sub(r'<iframe[^>]*>.*?</iframe>', '', clean_html, flags=re.DOTALL | re.IGNORECASE)
        clean_html = re.sub(r'<object[^>]*>.*?</object>', '', clean_html, flags=re.DOTALL | re.IGNORECASE)
        clean_html = re.sub(r'<embed[^>]*>', '', clean_html, flags=re.IGNORECASE)
        clean_html = re.sub(r'\son\w+\s*=\s*["\'][^"\']*["\']', '', clean_html, flags=re.IGNORECASE)
        logger.warning("bleach 未安装，使用正则兜底清理 HTML，建议安装 bleach: pip install bleach")

    return clean_html


def strip_markdown(text: str, max_length: int = 200) -> str:
    """
    去除 Markdown 格式，返回纯文本摘要

    Args:
        text: Markdown 格式的文本
        max_length: 最大长度

    Returns:
        str: 纯文本摘要
    """
    if not text:
        return ""

    # 移除 Markdown 语法
    plain = re.sub(r'!\[.*?\]\(.*?\)', '', text)          # 图片
    plain = re.sub(r'\[([^\]]+)\]\(.*?\)', r'\1', plain)   # 链接保留文字
    plain = re.sub(r'#{1,6}\s*', '', plain)                 # 标题
    plain = re.sub(r'(\*{1,3}|_{1,3})(.*?)\1', r'\2', plain)  # 加粗/斜体
    plain = re.sub(r'~~(.*?)~~', r'\1', plain)               # 删除线
    plain = re.sub(r'`{1,3}[^`]*?`{1,3}', '', plain)        # 行内代码
    plain = re.sub(r'>\s?', '', plain)                       # 引用
    plain = re.sub(r'[-*+]\s', '', plain)                   # 无序列表
    plain = re.sub(r'\d+\.\s', '', plain)                   # 有序列表
    plain = re.sub(r'---+|\*\*\*+|___+', '', plain)          # 分隔线
    plain = re.sub(r'\n{2,}', '\n', plain)                  # 多余换行
    plain = plain.strip()

    if len(plain) > max_length:
        plain = plain[:max_length] + "..."

    return plain


def sanitize_html(text: str) -> str:
    """
    清理用户提交的 HTML，移除危险标签和属性，防止 XSS 攻击。

    Args:
        text: 用户提交的 HTML 字符串

    Returns:
        str: 清理后的安全 HTML
    """
    if not text:
        return ""

    if BLEACH_AVAILABLE:
        clean_html = bleach.clean(
            text,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            protocols=ALLOWED_PROTOCOLS,
            strip=True,
        )
    else:
        # bleach 不可用时，使用正则移除危险标签作为兜底
        clean_html = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        clean_html = re.sub(r'<iframe[^>]*>.*?</iframe>', '', clean_html, flags=re.DOTALL | re.IGNORECASE)
        clean_html = re.sub(r'<object[^>]*>.*?</object>', '', clean_html, flags=re.DOTALL | re.IGNORECASE)
        clean_html = re.sub(r'<embed[^>]*>', '', clean_html, flags=re.IGNORECASE)
        clean_html = re.sub(r'\son\w+\s*=\s*["\'][^"\']*["\']', '', clean_html, flags=re.IGNORECASE)
        clean_html = re.sub(r'<[^>]+>', '', clean_html)
        logger.warning("bleach 未安装，使用正则兜底清理 HTML，建议安装 bleach: pip install bleach")

    return clean_html


def render_content(content: str, content_format: str = "markdown") -> str:
    """
    根据内容格式统一渲染为安全的 HTML

    Args:
        content: 原始内容
        content_format: 内容格式（markdown / html / plain）

    Returns:
        str: 渲染后的安全 HTML
    """
    if not content:
        return ""

    if content_format == "html":
        # HTML 格式：清理危险标签
        return sanitize_html(content)
    elif content_format == "plain":
        # 纯文本：转义 HTML 特殊字符，换行转 <br>
        escaped = html_module.escape(content)
        escaped = escaped.replace("\n", "<br>")
        return f"<p>{escaped}</p>"
    else:
        # Markdown 格式（默认）
        return render_markdown(content)


def generate_summary(content: str, content_format: str = "markdown", max_length: int = 200) -> str:
    """
    根据内容格式生成纯文本摘要

    Args:
        content: 原始内容
        content_format: 内容格式
        max_length: 最大长度

    Returns:
        str: 纯文本摘要
    """
    if not content:
        return ""

    if content_format == "html":
        # HTML 格式：移除标签后取摘要
        plain = re.sub(r'<[^>]+>', '', content)
        plain = re.sub(r'&[a-zA-Z]+;', ' ', plain)  # HTML 实体
        plain = re.sub(r'\s+', ' ', plain).strip()
    elif content_format == "plain":
        plain = content.strip()
    else:
        # Markdown 格式
        plain = strip_markdown(content, max_length=max_length * 2)  # 先去格式

    if len(plain) > max_length:
        plain = plain[:max_length] + "..."

    return plain
