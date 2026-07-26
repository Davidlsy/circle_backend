# 更新日志 v1.0.40

## 版本信息
- **版本号**: v1.0.40
- **发布日期**: 2026-05-14
- **更新类型**: 功能新增

## 更新概述

本次更新新增**视频封面编辑功能**，支持用户上传自定义图片作为视频封面，或从视频中选择指定时间点截取帧作为封面。

---

## 新增功能

### 1. 视频封面编辑功能

#### 1.1 API 接口

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 更新封面 | PATCH | `/posts/videos/{id}/thumbnail` | 编辑视频封面 | 作者 |

#### 1.2 更新封面接口详情

- **路径**: `PATCH /posts/videos/{video_id}/thumbnail`
- **请求方式**: 支持两种方式（二选一）
  - **方式1**: 上传自定义图片
    - `Content-Type: multipart/form-data`
    - `thumbnail_file`: 图片文件
  - **方式2**: 从视频截取
    - `Content-Type: application/json`
    - `time_seconds`: 视频时间点（秒）
- **限制**:
  - 封面图片最大 **5MB**
  - 支持格式：**JPEG、PNG、GIF、WebP**
  - 时间点必须在视频时长范围内
- **返回**:
  ```json
  {
    "msg": "视频封面已更新",
    "thumbnail_url": "/uploads/abc123.jpg"
  }
  ```

#### 1.3 使用示例

**方式1：上传自定义图片**
```bash
curl -X PATCH "http://localhost:8000/posts/videos/1/thumbnail" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "thumbnail_file=@custom_cover.jpg"
```

**方式2：从视频截取（第10秒）**
```bash
curl -X PATCH "http://localhost:8000/posts/videos/1/thumbnail" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"time_seconds": 10}'
```

#### 1.4 请求 Schema

```python
class VideoThumbnailUpdateRequest(BaseModel):
    """更新视频封面请求"""
    time_seconds: Optional[int] = Field(
        None, 
        ge=0, 
        description="从视频中截取封面的时间点（秒），不传则使用上传的图片"
    )

class VideoThumbnailUpdateResponse(BaseModel):
    """更新视频封面响应"""
    msg: str
    thumbnail_url: str
```

---

### 2. 视频帧提取工具

新增 `extract_frame_at_time()` 函数，支持从视频指定时间点提取帧：

| 函数 | 功能 |
|------|------|
| `extract_frame_at_time()` | 从视频指定时间点提取帧作为封面 |
| `_extract_frame_at_time_cv2()` | OpenCV 实现 |
| `_extract_frame_at_time_ffmpeg()` | FFmpeg 备用实现 |

**实现方式**:
- 优先使用 **OpenCV (cv2)** 提取
- 备选使用 **FFmpeg** 命令行工具
- 自动处理时间点边界（超出时长则取最后一帧）
- 封面图宽度限制为 640px

---

## 文件变更

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/schemas.py` | 新增 VideoThumbnailUpdateRequest、VideoThumbnailUpdateResponse |
| `app/utils/video_utils.py` | 新增 extract_frame_at_time() 及相关函数 |
| `app/routers/post_router.py` | 新增更新视频封面接口 |
| `app/main.py` | 更新版本号至 1.0.40 |

---

## 功能特性

### 封面编辑方式

| 方式 | 说明 | 使用场景 |
|------|------|----------|
| 上传图片 | 使用自定义图片作为封面 | 用户有精心设计的封面图 |
| 视频截取 | 从视频指定时间点截取帧 | 选择视频中最精彩的画面 |

### 安全特性

| 特性 | 说明 |
|------|------|
| 图片格式验证 | 强制检查 content_type，仅允许 JPEG/PNG/GIF/WebP |
| 图片大小限制 | 封面图片最大 5MB |
| 图片内容验证 | PIL 验证图片有效性 |
| 时间点验证 | 检查时间点是否在视频时长范围内 |
| 权限控制 | 仅视频所属帖子作者可编辑封面 |
| 旧封面清理 | 自动删除旧封面文件 |

---

## 使用流程

### 1. 上传视频（已有功能）
```bash
curl -X POST "http://localhost:8000/posts/123/videos" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "files=@video.mp4"
# 返回视频ID，例如：1
```

### 2. 更新封面（新增功能）
```bash
# 方式1：上传自定义封面
curl -X PATCH "http://localhost:8000/posts/videos/1/thumbnail" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "thumbnail_file=@cover.jpg"

# 方式2：从视频第5秒截取
curl -X PATCH "http://localhost:8000/posts/videos/1/thumbnail" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"time_seconds": 5}'
```

### 3. 查看结果
```bash
curl "http://localhost:8000/posts/123"
# 返回的 videos 列表中包含更新后的 thumbnail_url
```

---

## 验证清单

- [x] 上传自定义图片作为封面
- [x] 从视频指定时间点截取封面
- [x] 图片格式验证
- [x] 图片大小限制
- [x] 图片内容验证
- [x] 时间点范围验证
- [x] 权限控制
- [x] 旧封面自动清理
- [x] OpenCV 帧提取实现
- [x] FFmpeg 备用实现
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
