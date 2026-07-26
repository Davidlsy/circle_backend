from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.database import get_db
from app.models import User, Post, Tag, PostTag
from app.schemas import (
    TagPublic, TagList, PostTagPublic,
    AddTagsRequest, Msg
)
from app.auth import get_current_active_user

router = APIRouter(prefix="/tags", tags=["话题/标签"])


# ─── 标签管理 ───

@router.get("/", response_model=TagList)
def list_tags(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    获取话题列表（按帖子数倒序）
    """
    query = db.query(Tag)
    total = query.count()
    tags = query.order_by(Tag.post_count.desc(), Tag.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()
    return TagList(tags=[TagPublic.model_validate(t) for t in tags], total=total)


@router.get("/search", response_model=TagList)
def search_tags(
    q: str = Query(..., min_length=1, max_length=50),
    db: Session = Depends(get_db)
):
    """
    搜索话题（按名称模糊匹配，最多返回20条）
    """
    tags = db.query(Tag).filter(
        Tag.name.like(f"%{q}%")
    ).order_by(Tag.post_count.desc()).limit(20).all()
    return TagList(tags=[TagPublic.model_validate(t) for t in tags], total=len(tags))


@router.post("/", response_model=TagPublic, status_code=201)
def create_tag(
    name: str = Query(..., min_length=1, max_length=50),
    description: str = Query(None, max_length=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    创建新话题（需登录）
    话题名唯一，已存在则返回已有话题
    """
    existing = db.query(Tag).filter(Tag.name == name).first()
    if existing:
        return TagPublic.model_validate(existing)

    tag = Tag(name=name, description=description)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return TagPublic.model_validate(tag)


# ─── 帖子标签操作 ───

@router.post("/posts/{post_id}", response_model=List[TagPublic])
def set_post_tags(
    post_id: int,
    data: AddTagsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    为帖子设置标签（替换模式：先删后加）
    - 最多 9 个标签
    - 仅帖子作者可操作
    - 标签不存在则报错
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    if post.author_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权修改此帖子")

    # 校验标签都存在
    tags = db.query(Tag).filter(Tag.id.in_(data.tag_ids)).all()
    if len(tags) != len(data.tag_ids):
        found_ids = {t.id for t in tags}
        missing = set(data.tag_ids) - found_ids
        raise HTTPException(status_code=404, detail=f"标签不存在: {missing}")

    # 删除旧关联
    old_tags = db.query(PostTag).filter(PostTag.post_id == post_id).all()
    for pt in old_tags:
        # 减少旧标签的 post_count
        tag = db.query(Tag).filter(Tag.id == pt.tag_id).first()
        if tag and tag.post_count > 0:
            tag.post_count -= 1
        db.delete(pt)

    # 创建新关联
    for tag_id in data.tag_ids:
        db.add(PostTag(post_id=post_id, tag_id=tag_id))
        # 增加 post_count
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if tag:
            tag.post_count += 1

    db.commit()

    # 返回更新后的标签列表
    post_tags = db.query(PostTag).filter(PostTag.post_id == post_id).all()
    result = []
    for pt in post_tags:
        db.refresh(pt.tag)
        result.append(TagPublic.model_validate(pt.tag))
    return result


@router.get("/posts/{post_id}", response_model=List[TagPublic])
def get_post_tags(
    post_id: int,
    db: Session = Depends(get_db)
):
    """
    获取帖子的所有标签
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    post_tags = db.query(PostTag).filter(PostTag.post_id == post_id).all()
    result = []
    for pt in post_tags:
        db.refresh(pt.tag)
        result.append(TagPublic.model_validate(pt.tag))
    return result


@router.delete("/posts/{post_id}/{tag_id}", response_model=Msg)
def remove_post_tag(
    post_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    从帖子移除单个标签（仅作者或超管）
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    if post.author_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权修改此帖子")

    post_tag = db.query(PostTag).filter(
        PostTag.post_id == post_id,
        PostTag.tag_id == tag_id
    ).first()
    if not post_tag:
        raise HTTPException(status_code=404, detail="该帖子没有此标签")

    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if tag and tag.post_count > 0:
        tag.post_count -= 1

    db.delete(post_tag)
    db.commit()
    return Msg(msg="标签已移除")


# ─── 话题下的帖子列表 ───

@router.get("/{tag_id}/posts", response_model=dict)
def get_posts_by_tag(
    tag_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    获取指定话题下的帖子列表
    返回格式与 /posts/ 一致
    """
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="话题不存在")

    query = db.query(Post).join(PostTag).filter(
        PostTag.tag_id == tag_id,
        Post.is_published == True
    )

    total = query.distinct().count()
    posts = query.order_by(Post.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()

    return {
        "tag": TagPublic.model_validate(tag),
        "posts": posts,
        "total": total,
        "page": page,
        "page_size": page_size
    }
