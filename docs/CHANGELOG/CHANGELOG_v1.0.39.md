# 更新日志 v1.0.39

## 版本信息
- **版本号**: v1.0.39
- **发布日期**: 2026-05-14
- **更新类型**: 功能新增

## 更新概述

本次更新新增**视频上传功能**，支持用户在帖子中上传视频，包含视频信息提取、封面生成、时长限制等功能。

---

## 新增功能

### 1. 视频上传功能

#### 1.1 数据模型

新增 `PostVideo` 模型存储视频信息：

```python
class PostVideo(Base):
    """帖子视频表"""
    __tablename__ = "post_videos"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    url = Column(String(500), nullable=False)           # 视频访问路径
    filename = Column(String(255), nullable=False)      # 原始文件名
    size = Column(Integer, nullable=False)              # 文件大小（字节）
    duration = Column(Integer, nullable=False)          # 视频时长（秒）
    width = Column(Integer, nullable=True)              # 视频宽度
    height = Column(Integer, nullable=True)             # 视频高度
    thumbnail_url = Column(String(500), nullable=True)  # 视频封面图URL
    order = Column(Integer, default=0)                  # 排序
    created_at = Column(DateTime, default=datetime.utcnow)
```

#### 1.2 API 接口

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 上传视频 | POST | `/posts/{id}/videos` | 上传视频到帖子 | 作者 |
| 获取视频 | GET | `/posts/{id}/videos` | 获取帖子视频列表 | 公开 |
| 删除视频 | DELETE | `/posts/videos/{id}` | 删除指定视频 | 作者 |

#### 1.3 上传视频接口详情

- **路径**: `POST /posts/{post_id}/videos`
- **请求**: `multipart/form-data`，支持多文件上传
- **限制**:
  - 单视频最大 **100MB**
  - 视频最长 **5 分钟**
  - 单篇帖子最多 **3 个视频**
  - 支持格式：**MP4、MOV、WebM、AVI**
- **功能**:
  - 自动提取视频信息（时长、分辨率）
  - 自动生成视频封面图（第一帧）
  - 视频内容验证
- **返回**:
  ```json
  {
    "msg": "成功上传 1 个视频",
    "video": {
      "id": 1,
      "post_id": 123,
      "url": "/uploads/abc123.mp4",
      "filename": "video.mp4",
      "size": 52428800,
      "duration": 120,
      "width": 1920,
      "height": 1080,
      "thumbnail_url": "/uploads/def456.jpg",
      "order": 0,
      "created_at": "2026-05-14T10:00:00"
    }
  }
  ```

#### 1.4 视频 Schema

```python
class PostVideoPublic(BaseModel):
    id: int
    post_id: int
    url: str
    filename: str
    size: int
    duration: int                    # 视频时长（秒）
    width: Optional[int] = None      # 视频宽度
    height: Optional[int] = None     # 视频高度
    thumbnail_url: Optional[str] = None  # 视频封面图URL
    order: int
    created_at: datetime
```

#### 1.5 帖子详情更新

帖子详情接口现在返回视频列表：

```json
{
  "id": 123,
  "title": "帖子标题",
  "content": "帖子内容",
  "images": [...],
  "videos": [...],  // 新增视频列表
  "tags": [...],
  ...
}
```

---

### 2. 视频处理工具

新增 `app/utils/video_utils.py` 模块，提供视频处理功能：

| 函数 | 功能 |
|------|------|
| `get_video_info()` | 获取视频信息（时长、分辨率） |
| `generate_thumbnail()` | 生成视频封面图 |
| `validate_video_content()` | 验证视频内容有效性 |

**实现方式**:
- 优先使用 **OpenCV (cv2)** 处理
- 备选使用 **FFmpeg** 命令行工具
- 支持自动降级

---

### 3. 配置更新

新增视频相关配置：

```python
# 视频上传配置
MAX_VIDEO_SIZE: int = 100 * 1024 * 1024        # 单个视频最大 100MB
MAX_VIDEOS_PER_POST: int = 3                    # 单篇帖子最多 3 个视频
MAX_VIDEO_DURATION: int = 300                   # 视频最大时长（秒），默认 5 分钟
ALLOWED_VIDEO_TYPES: list = ["video/mp4", "video/quicktime", "video/webm", "video/x-msvideo"]
VIDEO_THUMBNAIL_WIDTH: int = 640               # 视频封面图宽度
```

---

## 文件变更

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `app/utils/__init__.py` | 工具函数包初始化 |
| `app/utils/video_utils.py` | 视频处理工具函数 |

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/models.py` | 新增 PostVideo 模型，更新 Post 关系 |
| `app/config.py` | 新增视频上传配置 |
| `app/schemas.py` | 新增 PostVideoPublic、VideoUploadResponse、VideoDeleteResponse |
| `app/routers/post_router.py` | 新增视频上传、获取、删除接口，更新帖子详情返回视频 |
| `app/main.py` | 更新版本号至 1.0.39 |

---

## 依赖安装

视频处理需要安装以下依赖：

```bash
# 方式1：使用 OpenCV（推荐）
pip install opencv-python-headless

# 方式2：使用 FFmpeg（备选）
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# 下载 FFmpeg 并添加到 PATH
```

---

## 数据库迁移

需要执行数据库迁移创建新表：

```bash
alembic revision --autogenerate -m "add_post_video_table"
alembic upgrade head
```

---

## 使用示例

### 上传视频

```bash
curl -X POST "http://localhost:8000/posts/123/videos" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "files=@video.mp4"
```

### 获取帖子视频

```bash
curl "http://localhost:8000/posts/123/videos"
```

### 删除视频

```bash
curl -X DELETE "http://localhost:8000/posts/videos/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 安全特性

| 特性 | 说明 |
|------|------|
| 文件类型验证 | 强制检查 content_type，仅允许 MP4/MOV/WebM/AVI |
| 文件大小限制 | 单视频最大 100MB |
| 视频时长限制 | 最长 5 分钟 |
| 内容验证 | 提取视频信息验证文件有效性 |
| 权限控制 | 仅帖子作者可上传/删除视频 |
| 文件名安全 | UUID 重命名，防止路径遍历 |

---

## 性能优化

- 视频封面图宽度限制为 640px，减少存储和传输
- 批量查询帖子视频，避免 N+1 问题
- 视频信息提取使用高效的 OpenCV 库

---

## 验证清单

- [x] PostVideo 数据模型
- [x] 视频上传接口
- [x] 视频获取接口
- [x] 视频删除接口
- [x] 视频信息提取（时长、分辨率）
- [x] 视频封面生成
- [x] 帖子详情返回视频列表
- [x] 视频配置参数
- [x] 视频内容验证
- [x] 权限控制
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
