from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.database import get_db
from app.models import User, Post, Comment, Like, Collection, PostImage, Follow
from app.schemas import (
    PostDetail, PostList, Msg, UserPublic, PostImagePublic
)
from app.auth import get_current_active_user

router = APIRouter(prefix="/feed", tags=["动态流"])


def _build_post_detail(db: Session, p: Post, current_user_id: Optional[int] = None) -> PostDetail:
    """构建 PostDetail（含评论数/点赞数/是否点赞/收藏数/是否收藏/图片）"""
    comment_count = db.query(func.count(Comment.id)).filter(Comment.post_id == p.id).scalar()
    like_count = db.query(func.count(Like.id)).filter(Like.post_id == p.id).scalar()

    is_liked = False
    is_collected = False
    if current_user_id:
        is_liked = db.query(Like).filter(
            Like.post_id == p.id, Like.user_id == current_user_id
        ).first() is not None
        is_collected = db.query(Collection).filter(
            Collection.post_id == p.id, Collection.user_id == current_user_id
        ).first() is not None

    images = db.query(PostImage).filter(
        PostImage.post_id == p.id
    ).order_by(PostImage.order, PostImage.created_at).all()

    return PostDetail(
        id=p.id,
        title=p.title,
        content=p.content,
        author_id=p.author_id,
        is_published=p.is_published,
        view_count=p.view_count,
        created_at=p.created_at,
        updated_at=p.updated_at,
        author=UserPublic.model_validate(p.author),
        comment_count=comment_count,
        like_count=like_count,
        is_liked=is_liked,
        collection_count=0,
        is_collected=is_collected,
        images=[PostImagePublic.model_validate(img) for img in images],
        status=p.status
    )


@router.get("/", response_model=PostList)
def get_feed(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取动态流（关注用户的帖子）

    - 返回当前用户关注的所有用户发布的帖子
    - 按发布时间倒序
    - 分页展示
    - 需登录
    """
    # 获取当前用户关注的所有用户ID
    following_ids = db.query(Follow.following_id).filter(
        Follow.follower_id == current_user.id
    ).all()
    following_id_list = [f[0] for f in following_ids]

    if not following_id_list:
        return PostList(posts=[], total=0, page=page, page_size=page_size)

    # 查询这些用户发布的帖子
    query = db.query(Post).filter(
        Post.author_id.in_(following_id_list),
        Post.is_published == True,
        Post.status == "approved"  # 只显示审核通过的帖子
    )

    total = query.count()
    posts = query.order_by(Post.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()

    post_details = [_build_post_detail(db, p, current_user.id) for p in posts]
    return PostList(posts=post_details, total=total, page=page, page_size=page_size)
