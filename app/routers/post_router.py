from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
import os
import uuid
import shutil
import io
import errno

from app.database import get_db
from app.models import User, Post, Comment, Like, CommentLike, PostImage, PostVideo, Collection, Tag, PostTag
from app.schemas import (
    PostCreate, PostUpdate, PostPublic, PostDetail, PostList,
    CommentCreate, CommentUpdate, CommentPublic, CommentWithAuthor,
    LikeResponse, Msg, UserPublic, PostImagePublic, PostVideoPublic,
    ImageUploadResponse, ImageDeleteResponse, CollectionResponse,
    TagPublic, VideoUploadResponse, VideoDeleteResponse,
    VideoThumbnailUpdateRequest, VideoThumbnailUpdateResponse,
    CommentLikeResponse
)
from app.auth import get_current_active_user, get_current_active_user_optional
from app.config import get_settings
from app.logging_config import logger
from app.utils.video_utils import (
    get_video_info, generate_thumbnail, validate_video_content,
    VIDEO_CONTENT_TYPE_TO_EXT
)
from app.utils.markdown_utils import render_markdown, strip_markdown, render_content, generate_summary

try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL 未安装，图片内容验证功能不可用")

settings = get_settings()
router = APIRouter(prefix="/posts", tags=["帖子"])

# 文件扩展名映射表（强制使用标准扩展名）
CONTENT_TYPE_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


# ─── 工具函数 ───

def _ensure_upload_dir():
    """确保上传目录存在"""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


def _validate_image_content(content: bytes) -> None:
    """
    验证文件内容是否为有效的图片

    Args:
        content: 文件内容字节

    Raises:
        HTTPException: 当文件不是有效图片时
    """
    if not PIL_AVAILABLE:
        logger.warning("PIL 未安装，跳过图片内容验证")
        return

    try:
        img = PILImage.open(io.BytesIO(content))
        # verify 会检查文件是否损坏，但不会加载像素数据
        img.verify()

        # 重新打开以获取格式信息（verify 会关闭文件）
        img = PILImage.open(io.BytesIO(content))
        img_format = img.format.lower() if img.format else ""

        # 检查格式是否在允许列表中
        allowed_formats = ["jpeg", "png", "gif", "webp"]
        if img_format not in allowed_formats:
            raise HTTPException(
                status_code=400,
                detail=f"无效的图片格式: {img_format}，仅支持: {', '.join(allowed_formats)}"
            )

        # 检查 content_type 与实际格式是否匹配
        format_to_content_type = {
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
        }
        expected_content_type = format_to_content_type.get(img_format)

    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"图片内容验证失败: {e}")
        raise HTTPException(status_code=400, detail="上传的文件不是有效的图片")


def _save_image_file(file: UploadFile) -> tuple[str, int]:
    """
    保存图片文件，返回 (filename, size)
    不返回完整 URL，路径存储在数据库，URL 由静态文件服务提供
    """
    _ensure_upload_dir()

    # 校验文件类型
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的图片格式，仅支持：{', '.join(settings.ALLOWED_IMAGE_TYPES)}"
        )

    # 读取内容校验大小
    content = file.file.read()
    size = len(content)

    if size > settings.MAX_IMAGE_SIZE:
        max_mb = settings.MAX_IMAGE_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"单张图片大小不能超过 {max_mb:.0f}MB，当前 {size / (1024*1024):.2f}MB"
        )

    if size == 0:
        raise HTTPException(status_code=400, detail="图片文件不能为空")

    # 验证图片内容有效性
    _validate_image_content(content)

    # 生成唯一文件名，根据 content_type 强制使用标准扩展名
    ext = CONTENT_TYPE_TO_EXT.get(file.content_type, ".jpg")
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_name)

    # 写文件
    with open(file_path, "wb") as f:
        f.write(content)

    return unique_name, size


def _build_image_url(filename: str, base_url: str = "/uploads") -> str:
    """构建图片的访问 URL"""
    return f"{base_url}/{filename}"


def _get_post_images(post_id: int, db: Session) -> List[PostImagePublic]:
    """获取帖子的图片列表"""
    images = db.query(PostImage).filter(
        PostImage.post_id == post_id
    ).order_by(PostImage.order, PostImage.created_at).all()
    return [PostImagePublic.model_validate(img) for img in images]


def _get_post_tags(post_id: int, db: Session) -> List[TagPublic]:
    """获取帖子的标签列表"""
    post_tags = db.query(PostTag).filter(PostTag.post_id == post_id).all()
    result = []
    for pt in post_tags:
        db.refresh(pt.tag)
        result.append(TagPublic.model_validate(pt.tag))
    return result


def _get_post_videos(post_id: int, db: Session) -> List[PostVideoPublic]:
    """获取帖子的视频列表"""
    videos = db.query(PostVideo).filter(
        PostVideo.post_id == post_id
    ).order_by(PostVideo.order, PostVideo.created_at).all()
    return [PostVideoPublic.model_validate(v) for v in videos]


# ─── 帖子 CRUD ───

@router.post("/", response_model=PostPublic, status_code=status.HTTP_201_CREATED)
def create_post(
    post: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """创建帖子（需审核：普通用户 pending，管理员 approved），必须关联明星，仅已通过的粉丝可发帖"""
    from app.models import Star, StarPost, StarFan

    # 验证明星是否存在
    star = db.query(Star).filter(Star.id == post.star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在或已禁用")

    # 验证用户是否是该明星的已通过粉丝（管理员跳过）
    if not current_user.is_superuser:
        is_fan = db.query(StarFan).filter(
            StarFan.star_id == post.star_id,
            StarFan.user_id == current_user.id,
            StarFan.status == "approved"
        ).first()
        if not is_fan:
            raise HTTPException(
                status_code=403,
                detail="仅该明星的已通过粉丝可以发帖，请先申请成为粉丝"
            )

    initial_status = "approved" if current_user.is_superuser else "pending"
    db_post = Post(
        title=post.title,
        content=post.content,
        content_format=post.content_format,
        author_id=current_user.id,
        is_published=post.is_published,
        status=initial_status
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)

    # 关联到明星
    star_post = StarPost(star_id=post.star_id, post_id=db_post.id)
    db.add(star_post)

    # 更新明星帖子数
    star.post_count = db.query(func.count(StarPost.id)).filter(
        StarPost.star_id == post.star_id
    ).scalar() + 1

    db.commit()

    # 返回帖子详情（包含明星信息）
    result = PostPublic.model_validate(db_post)
    result.content_html = render_content(db_post.content, db_post.content_format)
    result.content_summary = generate_summary(db_post.content, db_post.content_format, 200)
    return result


@router.get("/", response_model=PostList)
def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    author_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_active_user)
):
    """获取帖子列表（分页，仅审核通过的帖子）"""
    query = db.query(Post).filter(Post.is_published == True)

    if current_user:
        # 作者本人可看自己的所有帖子（pending/approved/rejected），其他人只看 approved
        query = query.filter(
            (Post.author_id == current_user.id) | (Post.status == "approved")
        )
    else:
        query = query.filter(Post.status == "approved")

    if author_id:
        query = query.filter(Post.author_id == author_id)

    total = query.count()
    posts = query.order_by(Post.is_pinned.desc(), Post.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()

    # 优化：批量查询统计数据，避免 N+1 问题
    post_ids = [p.id for p in posts]

    # 批量查询评论数
    comment_counts = {}
    if post_ids:
        comment_results = db.query(
            Comment.post_id,
            func.count(Comment.id).label('count')
        ).filter(Comment.post_id.in_(post_ids)).group_by(Comment.post_id).all()
        comment_counts = {r.post_id: r.count for r in comment_results}

    # 批量查询点赞数
    like_counts = {}
    if post_ids:
        like_results = db.query(
            Like.post_id,
            func.count(Like.id).label('count')
        ).filter(Like.post_id.in_(post_ids)).group_by(Like.post_id).all()
        like_counts = {r.post_id: r.count for r in like_results}

    # 批量查询收藏数
    collection_counts = {}
    if post_ids:
        collection_results = db.query(
            Collection.post_id,
            func.count(Collection.id).label('count')
        ).filter(Collection.post_id.in_(post_ids)).group_by(Collection.post_id).all()
        collection_counts = {r.post_id: r.count for r in collection_results}

    # 批量查询当前用户的点赞/收藏状态
    user_liked_ids = set()
    user_collected_ids = set()
    if current_user and post_ids:
        user_liked_ids = set(
            r[0] for r in db.query(Like.post_id).filter(
                Like.post_id.in_(post_ids),
                Like.user_id == current_user.id
            ).all()
        )
        user_collected_ids = set(
            r[0] for r in db.query(Collection.post_id).filter(
                Collection.post_id.in_(post_ids),
                Collection.user_id == current_user.id
            ).all()
        )

    # 批量查询帖子关联的明星
    from app.models import StarPost, Star
    star_links = db.query(StarPost).filter(
        StarPost.post_id.in_(post_ids)
    ).all()
    star_post_map = {sp.post_id: sp.star_id for sp in star_links}
    star_ids = list(set(star_post_map.values()))
    
    stars = {}
    if star_ids:
        star_records = db.query(Star).filter(Star.id.in_(star_ids)).all()
        stars = {s.id: s for s in star_records}

    post_details = []
    for p in posts:
        # 使用批量查询结果
        comment_count = comment_counts.get(p.id, 0)
        like_count = like_counts.get(p.id, 0)
        collection_count = collection_counts.get(p.id, 0)
        is_liked = p.id in user_liked_ids
        is_collected = p.id in user_collected_ids

        images = _get_post_images(p.id, db)
        videos = _get_post_videos(p.id, db)
        tags = _get_post_tags(p.id, db)

        # 获取关联的明星
        star = None
        star_id = star_post_map.get(p.id)
        if star_id and star_id in stars:
            from app.schemas import StarPublic
            star = StarPublic.model_validate(stars[star_id])

        post_details.append(PostDetail(
            id=p.id,
            title=p.title,
            content=p.content,
            content_format=p.content_format,
            content_html=render_content(p.content, p.content_format),
            content_summary=generate_summary(p.content, p.content_format, 200),
            author_id=p.author_id,
            is_published=p.is_published,
            view_count=p.view_count,
            created_at=p.created_at,
            updated_at=p.updated_at,
            author=UserPublic.model_validate(p.author),
            star=star,
            comment_count=comment_count,
            like_count=like_count,
            is_liked=is_liked,
            images=images,
            videos=videos,
            collection_count=collection_count,
            is_collected=is_collected,
            tags=tags,
            status=p.status
        ))

    return PostList(posts=post_details, total=total, page=page, page_size=page_size)


@router.get("/{post_id}", response_model=PostDetail)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_active_user)
):
    """获取帖子详情（未审核帖子仅作者和管理员可见）"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    # 非管理员且非作者只能看 approved 帖子
    if post.status != "approved":
        if not current_user or (current_user.id != post.author_id and not current_user.is_superuser):
            raise HTTPException(status_code=404, detail="帖子不存在")

    # 增加浏览量
    post.view_count += 1
    db.commit()

    comment_count = db.query(func.count(Comment.id)).filter(Comment.post_id == post.id).scalar()
    like_count = db.query(func.count(Like.id)).filter(Like.post_id == post.id).scalar()
    collection_count = db.query(func.count(Collection.id)).filter(Collection.post_id == post.id).scalar()
    images = _get_post_images(post.id, db)
    videos = _get_post_videos(post.id, db)
    tags = _get_post_tags(post.id, db)

    # 根据当前登录用户判断是否点赞/收藏
    is_liked = False
    is_collected = False
    if current_user:
        is_liked = db.query(Like).filter(
            Like.post_id == post.id,
            Like.user_id == current_user.id
        ).first() is not None
        is_collected = db.query(Collection).filter(
            Collection.post_id == post.id,
            Collection.user_id == current_user.id
        ).first() is not None

    # 获取关联的明星
    star = None
    star_link = db.query(StarPost).filter(StarPost.post_id == post.id).first()
    if star_link:
        star_record = db.query(Star).filter(Star.id == star_link.star_id).first()
        if star_record:
            from app.schemas import StarPublic
            star = StarPublic.model_validate(star_record)

    return PostDetail(
        id=post.id,
        title=post.title,
        content=post.content,
        content_format=post.content_format,
        content_html=render_content(post.content, post.content_format),
        content_summary=generate_summary(post.content, post.content_format, 200),
        author_id=post.author_id,
        is_published=post.is_published,
        view_count=post.view_count,
        created_at=post.created_at,
        updated_at=post.updated_at,
        author=UserPublic.model_validate(post.author),
        star=star,
        comment_count=comment_count,
        like_count=like_count,
        is_liked=is_liked,
        collection_count=collection_count,
        is_collected=is_collected,
        images=images,
        videos=videos,
        tags=tags,
        status=post.status
    )


@router.put("/{post_id}", response_model=PostPublic)
def update_post(
    post_id: int,
    post_update: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """更新帖子（仅作者）"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改此帖子")

    update_data = post_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(post, key, value)

    db.commit()
    db.refresh(post)
    return post


@router.delete("/{post_id}", response_model=Msg)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除帖子（仅作者或超级管理员）"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    if post.author_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权删除此帖子")

    # 删除帖子关联的本地图片文件
    images = db.query(PostImage).filter(PostImage.post_id == post_id).all()
    for img in images:
        file_path = os.path.join(settings.UPLOAD_DIR, os.path.basename(img.url))
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e:
                # 仅记录非"文件不存在"的错误
                if e.errno != errno.ENOENT:
                    logger.warning(f"删除帖子图片失败: {file_path}, 错误: {e}")

    db.delete(post)
    db.commit()
    return Msg(msg="帖子已删除")


# ─── 评论 CRUD ───

@router.post("/{post_id}/comments", response_model=CommentPublic, status_code=status.HTTP_201_CREATED)
def create_comment(
    post_id: int,
    comment: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """评论帖子"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    if comment.parent_id:
        parent = db.query(Comment).filter(Comment.id == comment.parent_id).first()
        if not parent or parent.post_id != post_id:
            raise HTTPException(status_code=400, detail="无效的回复目标")

    db_comment = Comment(
        content=comment.content,
        author_id=current_user.id,
        post_id=post_id,
        parent_id=comment.parent_id,
        status="approved" if current_user.is_superuser else "pending"
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment


@router.get("/{post_id}/comments", response_model=List[CommentWithAuthor])
def list_comments(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_active_user_optional)
):
    """获取帖子的评论列表"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    # 只显示审核通过的评论
    comments = db.query(Comment).filter(
        Comment.post_id == post_id,
        Comment.parent_id == None,
        Comment.status == "approved"
    ).order_by(Comment.created_at.desc()).all()

    if not comments:
        return []

    # 批量查询点赞数
    comment_ids = [c.id for c in comments]
    like_counts = {}
    if comment_ids:
        like_results = db.query(
            CommentLike.comment_id,
            func.count(CommentLike.id).label('count')
        ).filter(
            CommentLike.comment_id.in_(comment_ids)
        ).group_by(CommentLike.comment_id).all()
        like_counts = {r.comment_id: r.count for r in like_results}

    # 批量查询当前用户点赞状态
    user_liked_ids = set()
    if current_user and comment_ids:
        user_liked_ids = set(
            r[0] for r in db.query(CommentLike.comment_id).filter(
                CommentLike.comment_id.in_(comment_ids),
                CommentLike.user_id == current_user.id
            ).all()
        )

    return [CommentWithAuthor(
        id=c.id,
        content=c.content,
        author_id=c.author_id,
        post_id=c.post_id,
        parent_id=c.parent_id,
        status=c.status,
        created_at=c.created_at,
        updated_at=c.updated_at,
        author=UserPublic.model_validate(c.author),
        like_count=like_counts.get(c.id, 0),
        is_liked=c.id in user_liked_ids
    ) for c in comments]


@router.delete("/comments/{comment_id}", response_model=Msg)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除评论（仅作者或超级管理员）"""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    if comment.author_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权删除此评论")

    db.delete(comment)
    db.commit()
    return Msg(msg="评论已删除")


# ─── 评论点赞功能 ───

@router.post("/comments/{comment_id}/like", response_model=CommentLikeResponse)
def toggle_comment_like(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    评论点赞/取消点赞
    - 已点赞则取消，未点赞则添加
    - 返回当前点赞状态和点赞总数
    """
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")

    # 查找是否已点赞
    existing_like = db.query(CommentLike).filter(
        CommentLike.comment_id == comment_id,
        CommentLike.user_id == current_user.id
    ).first()

    if existing_like:
        # 已点赞 → 取消点赞
        db.delete(existing_like)
        db.commit()
        is_liked = False
        msg = "已取消点赞"
    else:
        # 未点赞 → 添加点赞
        comment_like = CommentLike(
            comment_id=comment_id,
            user_id=current_user.id
        )
        db.add(comment_like)
        db.commit()
        is_liked = True
        msg = "已点赞"

    # 获取最新点赞数
    like_count = db.query(func.count(CommentLike.id)).filter(
        CommentLike.comment_id == comment_id
    ).scalar()

    return CommentLikeResponse(
        msg=msg,
        is_liked=is_liked,
        like_count=like_count
    )


# ─── 点赞功能 ───

@router.post("/{post_id}/like", response_model=LikeResponse)
def toggle_like(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """切换帖子点赞状态"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    existing_like = db.query(Like).filter(
        Like.post_id == post_id,
        Like.user_id == current_user.id
    ).first()

    if existing_like:
        db.delete(existing_like)
        db.commit()
        liked = False
        msg = "取消点赞成功"
    else:
        new_like = Like(user_id=current_user.id, post_id=post_id)
        db.add(new_like)
        db.commit()
        liked = True
        msg = "点赞成功"

    like_count = db.query(func.count(Like.id)).filter(Like.post_id == post_id).scalar()
    return LikeResponse(msg=msg, liked=liked, like_count=like_count)


# ─── 图片上传 ───

@router.post("/{post_id}/images", response_model=ImageUploadResponse)
async def upload_images(
    post_id: int,
    files: List[UploadFile] = File(..., description="图片文件，最多9张，支持 jpeg/png/gif/webp"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    上传帖子图片

    - 单张图片最大 5MB
    - 单篇帖子最多 9 张图片
    - 支持格式：jpeg / png / gif / webp
    - 已有的图片不计入新上传数量限制检查
    - 图片 URL 通过 /uploads/{filename} 访问（需在 main.py 挂载静态文件）
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    if post.author_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权为此帖上传图片")

    # 已有图片数量
    existing_count = db.query(func.count(PostImage.id)).filter(
        PostImage.post_id == post_id
    ).scalar()

    if existing_count >= settings.MAX_IMAGES_PER_POST:
        raise HTTPException(
            status_code=400,
            detail=f"该帖子已达到最大图片数量上限（{settings.MAX_IMAGES_PER_POST}张）"
        )

    remaining_slots = settings.MAX_IMAGES_PER_POST - existing_count
    if len(files) > remaining_slots:
        raise HTTPException(
            status_code=400,
            detail=f"最多只能再上传 {remaining_slots} 张图片，该帖子已有 {existing_count} 张"
        )

    # 获取当前最大 order
    max_order = db.query(func.max(PostImage.order)).filter(
        PostImage.post_id == post_id
    ).scalar() or 0

    saved_images = []
    for i, file in enumerate(files):
        try:
            filename, size = _save_image_file(file)
            order = max_order + i + 1
            url = _build_image_url(filename)

            db_image = PostImage(
                post_id=post_id,
                url=url,
                filename=file.filename or filename,
                size=size,
                order=order
            )
            db.add(db_image)
            saved_images.append(db_image)
        except HTTPException:
            # 单张失败，回滚已保存的文件
            db.rollback()
            for saved in saved_images:
                fpath = os.path.join(settings.UPLOAD_DIR, os.path.basename(saved.url))
                if os.path.exists(fpath):
                    try:
                        os.remove(fpath)
                    except OSError:
                        pass
            raise

    db.commit()
    for img in saved_images:
        db.refresh(img)

    result = [PostImagePublic.model_validate(img) for img in saved_images]
    return ImageUploadResponse(
        images=result,
        uploaded_count=len(result),
        post_id=post_id
    )


@router.get("/{post_id}/images", response_model=List[PostImagePublic])
def get_post_images(
    post_id: int,
    db: Session = Depends(get_db)
):
    """获取帖子的所有图片"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    return _get_post_images(post_id, db)


@router.delete("/images/{image_id}", response_model=ImageDeleteResponse)
def delete_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除指定图片（仅帖子作者或超管）"""
    image = db.query(PostImage).filter(PostImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")

    post = db.query(Post).filter(Post.id == image.post_id).first()
    if post.author_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权删除此图片")

    # 删除本地文件
    filename = os.path.basename(image.url)
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    post_id = image.post_id
    db.delete(image)
    db.commit()

    remaining = db.query(func.count(PostImage.id)).filter(
        PostImage.post_id == post_id
    ).scalar()

    return ImageDeleteResponse(
        msg="图片已删除",
        remaining_count=remaining
    )


# ─── 视频上传功能 ───

def _save_video_file(file: UploadFile, post_id: int, db: Session) -> PostVideo:
    """
    保存视频文件，返回 PostVideo 对象
    """
    _ensure_upload_dir()

    # 校验文件类型
    if file.content_type not in settings.ALLOWED_VIDEO_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的视频格式，仅支持：{', '.join(settings.ALLOWED_VIDEO_TYPES)}"
        )

    # 读取内容校验大小
    content = file.file.read()
    size = len(content)

    if size > settings.MAX_VIDEO_SIZE:
        max_mb = settings.MAX_VIDEO_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"单个视频大小不能超过 {max_mb:.0f}MB，当前 {size / (1024*1024):.2f}MB"
        )

    if size == 0:
        raise HTTPException(status_code=400, detail="视频文件不能为空")

    # 验证视频内容（时长等）
    is_valid, error_msg = validate_video_content(content, settings.MAX_VIDEO_DURATION)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # 生成唯一文件名
    ext = VIDEO_CONTENT_TYPE_TO_EXT.get(file.content_type, ".mp4")
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_name)

    # 写文件
    with open(file_path, "wb") as f:
        f.write(content)

    # 获取视频信息
    video_info = get_video_info(file_path) or {"duration": 0, "width": 0, "height": 0}

    # 生成封面图
    thumbnail_name = f"{uuid.uuid4().hex}.jpg"
    thumbnail_path = os.path.join(settings.UPLOAD_DIR, thumbnail_name)
    thumbnail_generated = generate_thumbnail(file_path, thumbnail_path, settings.VIDEO_THUMBNAIL_WIDTH)

    # 保存到数据库
    video = PostVideo(
        post_id=post_id,
        url=f"/uploads/{unique_name}",
        filename=file.filename or unique_name,
        size=size,
        duration=video_info.get("duration", 0),
        width=video_info.get("width"),
        height=video_info.get("height"),
        thumbnail_url=f"/uploads/{thumbnail_name}" if thumbnail_generated else None,
        order=0  # 默认顺序
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    return video


@router.post("/{post_id}/videos", response_model=VideoUploadResponse)
def upload_videos(
    post_id: int,
    files: List[UploadFile] = File(..., description="视频文件，支持多个"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    上传视频到指定帖子
    - 仅帖子作者可操作
    - 支持同时上传多个视频
    - 单视频最大 100MB，最长 5 分钟
    - 支持格式：MP4, MOV, WebM, AVI
    - 自动生成视频封面图（第一帧）
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    if post.author_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权上传视频到此帖子")

    # 检查当前视频数量
    current_count = db.query(func.count(PostVideo.id)).filter(
        PostVideo.post_id == post_id
    ).scalar()

    if current_count + len(files) > settings.MAX_VIDEOS_PER_POST:
        raise HTTPException(
            status_code=400,
            detail=f"单篇帖子最多 {settings.MAX_VIDEOS_PER_POST} 个视频，当前已有 {current_count} 个"
        )

    uploaded_videos = []
    for file in files:
        try:
            video = _save_video_file(file, post_id, db)
            uploaded_videos.append(video)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"上传视频失败: {e}")
            raise HTTPException(status_code=500, detail=f"上传视频失败: {str(e)}")

    return VideoUploadResponse(
        msg=f"成功上传 {len(uploaded_videos)} 个视频",
        video=PostVideoPublic.model_validate(uploaded_videos[0]) if uploaded_videos else None
    )


@router.get("/{post_id}/videos", response_model=List[PostVideoPublic])
def get_post_videos(
    post_id: int,
    db: Session = Depends(get_db)
):
    """获取帖子的所有视频"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    videos = db.query(PostVideo).filter(
        PostVideo.post_id == post_id
    ).order_by(PostVideo.order, PostVideo.created_at).all()

    return [PostVideoPublic.model_validate(v) for v in videos]


@router.delete("/videos/{video_id}", response_model=VideoDeleteResponse)
def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除指定视频（仅帖子作者或超管）"""
    video = db.query(PostVideo).filter(PostVideo.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    post = db.query(Post).filter(Post.id == video.post_id).first()
    if post.author_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权删除此视频")

    # 删除本地文件
    filename = os.path.basename(video.url)
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                logger.warning(f"删除视频文件失败: {file_path}, 错误: {e}")

    # 删除封面图
    if video.thumbnail_url:
        thumb_filename = os.path.basename(video.thumbnail_url)
        thumb_path = os.path.join(settings.UPLOAD_DIR, thumb_filename)
        if os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    logger.warning(f"删除视频封面失败: {thumb_path}, 错误: {e}")

    db.delete(video)
    db.commit()

    return VideoDeleteResponse(msg="视频已删除")


# ─── 视频封面编辑功能 ───

@router.patch("/videos/{video_id}/thumbnail", response_model=VideoThumbnailUpdateResponse)
def update_video_thumbnail(
    video_id: int,
    data: VideoThumbnailUpdateRequest = VideoThumbnailUpdateRequest(),
    thumbnail_file: Optional[UploadFile] = File(None, description="自定义封面图片（可选），不传则使用 time_seconds 从视频中截取"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    更新视频封面
    - 方式1：上传自定义图片作为封面
    - 方式2：指定视频时间点（秒），从视频中截取该帧作为封面
    - 两种方式二选一，同时提供时优先使用上传的图片
    """
    video = db.query(PostVideo).filter(PostVideo.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    post = db.query(Post).filter(Post.id == video.post_id).first()
    if post.author_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权编辑此视频封面")

    # 获取视频文件路径
    video_filename = os.path.basename(video.url)
    video_path = os.path.join(settings.UPLOAD_DIR, video_filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="视频文件不存在")

    # 生成新的封面文件名
    new_thumbnail_name = f"{uuid.uuid4().hex}.jpg"
    new_thumbnail_path = os.path.join(settings.UPLOAD_DIR, new_thumbnail_name)

    thumbnail_generated = False

    # 方式1：使用上传的图片
    if thumbnail_file:
        # 验证图片格式
        if thumbnail_file.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的图片格式，仅支持：{', '.join(settings.ALLOWED_IMAGE_TYPES)}"
            )

        # 读取并保存图片
        content = thumbnail_file.file.read()
        if len(content) > settings.MAX_IMAGE_SIZE:
            max_mb = settings.MAX_IMAGE_SIZE / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"封面图片大小不能超过 {max_mb:.0f}MB"
            )

        # 验证图片内容
        _validate_image_content(content)

        # 保存图片
        with open(new_thumbnail_path, "wb") as f:
            f.write(content)
        thumbnail_generated = True

    # 方式2：从视频指定时间点截取
    elif data.time_seconds is not None:
        from app.utils.video_utils import extract_frame_at_time

        # 验证时间点
        if data.time_seconds < 0:
            raise HTTPException(status_code=400, detail="时间点不能为负数")
        if data.time_seconds > video.duration:
            raise HTTPException(
                status_code=400,
                detail=f"时间点超出视频时长（视频时长 {video.duration} 秒）"
            )

        # 提取帧
        thumbnail_generated = extract_frame_at_time(
            video_path,
            new_thumbnail_path,
            data.time_seconds,
            settings.VIDEO_THUMBNAIL_WIDTH
        )
        if not thumbnail_generated:
            raise HTTPException(status_code=500, detail="从视频截取封面失败")

    else:
        raise HTTPException(
            status_code=400,
            detail="请提供封面图片或指定视频时间点"
        )

    # 删除旧封面
    if video.thumbnail_url:
        old_thumb_filename = os.path.basename(video.thumbnail_url)
        old_thumb_path = os.path.join(settings.UPLOAD_DIR, old_thumb_filename)
        if os.path.exists(old_thumb_path):
            try:
                os.remove(old_thumb_path)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    logger.warning(f"删除旧封面失败: {old_thumb_path}, 错误: {e}")

    # 更新数据库
    video.thumbnail_url = f"/uploads/{new_thumbnail_name}"
    db.commit()
    db.refresh(video)

    return VideoThumbnailUpdateResponse(
        msg="视频封面已更新",
        thumbnail_url=video.thumbnail_url
    )


# ─── 收藏功能 ───

@router.post("/{post_id}/collect", response_model=CollectionResponse)
def toggle_collection(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """收藏/取消收藏帖子（toggle）"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    existing = db.query(Collection).filter(
        Collection.post_id == post_id,
        Collection.user_id == current_user.id
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        collected = False
        msg = "取消收藏成功"
    else:
        new_collection = Collection(user_id=current_user.id, post_id=post_id)
        db.add(new_collection)
        db.commit()
        collected = True
        msg = "收藏成功"

    collection_count = db.query(func.count(Collection.id)).filter(
        Collection.post_id == post_id
    ).scalar()

    return CollectionResponse(
        msg=msg,
        collected=collected,
        collection_count=collection_count
    )


# ─── 帖子推荐（基于热度） ───

def _calc_heat_score(post: Post, db: Session) -> float:
    """
    计算帖子热度分数
    公式：score = (view_count*1 + like_count*5 + comment_count*10 + collect_count*8) / hours^1.5
    hours: 帖子发布至今的小时数，加入时间衰减
    """
    from datetime import datetime
    now = datetime.utcnow()
    if not post.created_at:
        return 0.0
    hours = max((now - post.created_at).total_seconds() / 3600, 1)

    like_count = db.query(func.count(Like.id)).filter(Like.post_id == post.id).scalar() or 0
    comment_count = db.query(func.count(Comment.id)).filter(Comment.post_id == post.id).scalar() or 0
    collect_count = db.query(func.count(Collection.id)).filter(Collection.post_id == post.id).scalar() or 0

    raw = (post.view_count * 1 + like_count * 5 + comment_count * 10 + collect_count * 8)
    score = raw / (hours ** 1.5)
    return round(score, 4)


@router.get("/recommended", response_model=dict)
def get_recommended_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    star_id: Optional[int] = Query(None, description="按明星筛选"),
    db: Session = Depends(get_db)
):
    """获取热门推荐帖子（基于热度算法，公开）"""
    query = db.query(Post).filter(
        Post.is_published == True,
        Post.status == "approved"
    )

    if star_id:
        from app.models import StarPost
        star_post_ids = db.query(StarPost.post_id).filter(
            StarPost.star_id == star_id
        ).subquery()
        query = query.filter(Post.id.in_(star_post_ids))

    posts = query.all()

    # 计算每个帖子的热度并排序
    scored = []
    for p in posts:
        score = _calc_heat_score(p, db)
        scored.append((p, score))

    scored.sort(key=lambda x: x[1], reverse=True)

    total = len(scored)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = scored[start:end]

    from app.utils.markdown_utils import generate_summary

    post_list = []
    for p, score in page_items:
        author = db.query(User).filter(User.id == p.author_id).first()
        post_list.append({
            "id": p.id,
            "title": p.title,
            "content_summary": generate_summary(p.content, p.content_format, 200),
            "author_id": p.author_id,
            "author_name": author.username if author else "未知",
            "view_count": p.view_count,
            "like_count": db.query(func.count(Like.id)).filter(Like.post_id == p.id).scalar() or 0,
            "comment_count": db.query(func.count(Comment.id)).filter(Comment.post_id == p.id).scalar() or 0,
            "collect_count": db.query(func.count(Collection.id)).filter(Collection.post_id == p.id).scalar() or 0,
            "heat_score": score,
            "is_pinned": p.is_pinned,
            "is_featured": p.is_featured,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })

    return {"posts": post_list, "total": total, "page": page, "page_size": page_size}


# ─── 管理员：置顶 / 加精 ───

@router.post("/{post_id}/pin", response_model=Msg)
def toggle_pin_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """置顶/取消置顶帖子（仅管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅管理员可操作")

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    post.is_pinned = not post.is_pinned
    db.commit()

    return Msg(msg="已置顶" if post.is_pinned else "已取消置顶")


@router.post("/{post_id}/feature", response_model=Msg)
def toggle_feature_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """加精/取消加精帖子（仅管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅管理员可操作")

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    post.is_featured = not post.is_featured
    db.commit()

    return Msg(msg="已加精" if post.is_featured else "已取消加精")


@router.get("/featured", response_model=dict)
def list_featured_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取加精帖子列表（公开）"""
    query = db.query(Post).filter(
        Post.is_featured == True,
        Post.status == "approved",
        Post.is_published == True
    )

    total = query.count()
    posts = query.order_by(Post.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    from app.utils.markdown_utils import render_content, generate_summary

    post_list = []
    for p in posts:
        author = db.query(User).filter(User.id == p.author_id).first()
        post_list.append({
            "id": p.id,
            "title": p.title,
            "content_summary": generate_summary(p.content, p.content_format, 200),
            "author_id": p.author_id,
            "author_name": author.username if author else "未知",
            "view_count": p.view_count,
            "is_pinned": p.is_pinned,
            "is_featured": p.is_featured,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })

    return {"posts": post_list, "total": total, "page": page, "page_size": page_size}
