"""
用户模块路由

包含用户个人主页相关功能
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional

from app.database import get_db
from app.models import User, Post, StarPost, Star, FanBadge
from app.schemas import (
    PostPublic, PostList, UserPublic, FanBadgePublic, StarPublic
)
from app.auth import get_current_active_user
from app.logging_config import logger

router = APIRouter(prefix="/users", tags=["用户"])


# ─── 用户信息 ───

@router.get("/{user_id}", response_model=dict)
def get_user_profile(
    user_id: int,
    db: Session = Depends(get_db)
):
    """获取用户公开资料（含展示的粉丝牌）"""
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    result = {
        "id": user.id,
        "username": user.username,
        "avatar": user.avatar,
        "bio": user.bio,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }

    # 获取展示的粉丝牌
    display_badge = db.query(FanBadge).filter(
        FanBadge.user_id == user_id,
        FanBadge.is_displayed == True
    ).first()

    if display_badge:
        badge_result = FanBadgePublic.model_validate(display_badge)
        star = db.query(Star).filter(Star.id == display_badge.star_id).first()
        if star:
            badge_result.star = StarPublic.model_validate(star)
        result["display_badge"] = badge_result
    else:
        result["display_badge"] = None

    # 统计数据
    result["stats"] = {
        "post_count": db.query(func.count(Post.id)).filter(
            Post.author_id == user_id,
            Post.status == "approved"
        ).scalar() or 0
    }

    return result


# ─── 用户帖子展示 ───

@router.get("/{user_id}/posts", response_model=dict)
def get_user_posts(
    user_id: int,
    limit: int = Query(10, ge=1, le=50, description="展示数量限制"),
    days: int = Query(30, ge=1, le=365, description="时间范围（天）"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    获取用户发过的帖子（个人主页展示）
    
    参数说明：
    - limit: 展示数量限制（默认10，最大50）
    - days: 时间范围限制（默认30天，最大365天）
    - page: 页码
    - page_size: 每页数量
    
    返回：
    - 仅返回已审核通过的帖子
    - 按时间倒序排列
    - 可限制数量和时间范围
    """
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 计算时间范围
    time_threshold = datetime.utcnow() - timedelta(days=days)

    # 查询用户的帖子
    query = db.query(Post).filter(
        Post.author_id == user_id,
        Post.status == "approved",
        Post.created_at >= time_threshold
    )

    # 总数
    total = query.count()

    # 分页获取
    posts = query.order_by(Post.is_pinned.desc(), Post.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    # 构建返回结果
    post_list = []
    for p in posts:
        item = PostPublic.model_validate(p)
        # 获取帖子所属明星
        star_post = db.query(StarPost).filter(StarPost.post_id == p.id).first()
        if star_post:
            star = db.query(Star).filter(Star.id == star_post.star_id).first()
            if star:
                item.star_id = star.id
                item.star_name = star.name
        post_list.append(item)

    return {
        "posts": post_list,
        "total": total,
        "page": page,
        "page_size": page_size,
        "limit": limit,
        "days": days,
        "time_threshold": time_threshold.isoformat()
    }


@router.get("/{user_id}/posts/all", response_model=dict)
def get_user_all_posts(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    获取用户发过的所有帖子（无时间和数量限制）
    
    适用于查看用户完整发帖历史
    """
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    query = db.query(Post).filter(
        Post.author_id == user_id,
        Post.status == "approved"
    )

    total = query.count()
    posts = query.order_by(Post.is_pinned.desc(), Post.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    post_list = []
    for p in posts:
        item = PostPublic.model_validate(p)
        star_post = db.query(StarPost).filter(StarPost.post_id == p.id).first()
        if star_post:
            star = db.query(Star).filter(Star.id == star_post.star_id).first()
            if star:
                item.star_id = star.id
                item.star_name = star.name
        post_list.append(item)

    return {
        "posts": post_list,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/{user_id}/posts/by-star/{star_id}", response_model=dict)
def get_user_posts_by_star(
    user_id: int,
    star_id: int,
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(30, ge=1, le=365),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    获取用户在某明星板块发过的帖子
    
    适用于查看用户在特定粉丝圈的发帖记录
    """
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    star = db.query(Star).filter(Star.id == star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    time_threshold = datetime.utcnow() - timedelta(days=days)

    # 查询用户在该明星板块的帖子
    query = db.query(Post).join(StarPost).filter(
        Post.author_id == user_id,
        Post.status == "approved",
        StarPost.star_id == star_id,
        Post.created_at >= time_threshold
    )

    total = query.count()
    posts = query.order_by(Post.is_pinned.desc(), Post.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    post_list = [PostPublic.model_validate(p) for p in posts]

    return {
        "posts": post_list,
        "total": total,
        "page": page,
        "page_size": page_size,
        "star_id": star_id,
        "star_name": star.name,
        "limit": limit,
        "days": days
    }


# ─── 我的个人主页设置 ───

@router.get("/me/profile", response_model=dict)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取我的完整个人资料"""
    result = {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "avatar": current_user.avatar,
        "bio": current_user.bio,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }

    # 展示的粉丝牌
    display_badge = db.query(FanBadge).filter(
        FanBadge.user_id == current_user.id,
        FanBadge.is_displayed == True
    ).first()

    if display_badge:
        badge_result = FanBadgePublic.model_validate(display_badge)
        star = db.query(Star).filter(Star.id == display_badge.star_id).first()
        if star:
            badge_result.star = StarPublic.model_validate(star)
        result["display_badge"] = badge_result
    else:
        result["display_badge"] = None

    # 统计数据
    result["stats"] = {
        "post_count": db.query(func.count(Post.id)).filter(
            Post.author_id == current_user.id,
            Post.status == "approved"
        ).scalar() or 0,
        "like_received": db.query(func.sum(Post.like_count)).filter(
            Post.author_id == current_user.id,
            Post.status == "approved"
        ).scalar() or 0,
        "comment_received": db.query(func.sum(Post.comment_count)).filter(
            Post.author_id == current_user.id,
            Post.status == "approved"
        ).scalar() or 0
    }

    return result
