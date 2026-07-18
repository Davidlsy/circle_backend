"""
明星模块路由
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from app.database import get_db
from app.models import User, Star, StarPost, Post, StarFollow, StarFan
from app.schemas import (
    StarCreate, StarUpdate, StarPublic, StarList,
    StarPostCreate, StarPostPublic, StarRankingItem,
    PostCreate, PostPublic, Msg,
    StarFollowResponse, StarFollowerPublic, UserFollowingStarPublic,
    StarFanApplyRequest, StarFanReviewRequest, StarFanPublic, StarFanList,
    MyFanApplicationPublic
)
from app.auth import get_current_active_user
from app.logging_config import logger

router = APIRouter(prefix="/stars", tags=["明星"])


# ─── 明星资料管理 ───

@router.post("/", response_model=StarPublic, status_code=201)
def create_star(
    data: StarCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """创建明星资料（仅管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅管理员可创建明星资料")

    # 检查姓名是否已存在
    existing = db.query(Star).filter(Star.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="该明星已存在")

    star = Star(**data.model_dump())
    db.add(star)
    db.commit()
    db.refresh(star)
    return star


@router.get("/", response_model=StarList)
def list_stars(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db)
):
    """获取明星列表（支持搜索）"""
    query = db.query(Star).filter(Star.is_active == True)

    if keyword:
        query = query.filter(
            Star.name.contains(keyword) |
            Star.description.contains(keyword) |
            Star.profession.contains(keyword)
        )

    total = query.count()
    stars = query.order_by(Star.heat_score.desc(), Star.fan_count.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    return StarList(
        stars=[StarPublic.model_validate(s) for s in stars],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{star_id}", response_model=StarPublic)
def get_star(
    star_id: int,
    db: Session = Depends(get_db)
):
    """获取明星详情"""
    star = db.query(Star).filter(Star.id == star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")
    return star


@router.put("/{star_id}", response_model=StarPublic)
def update_star(
    star_id: int,
    data: StarUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """更新明星资料（仅管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅管理员可更新明星资料")

    star = db.query(Star).filter(Star.id == star_id).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(star, field, value)

    db.commit()
    db.refresh(star)
    return star


@router.delete("/{star_id}", response_model=Msg)
def delete_star(
    star_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除明星资料（仅管理员，软删除）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅管理员可删除明星资料")

    star = db.query(Star).filter(Star.id == star_id).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    star.is_active = False
    db.commit()
    return Msg(msg="明星资料已删除")


# ─── 明星帖子 ───

@router.post("/{star_id}/posts", response_model=PostPublic, status_code=201)
def create_star_post(
    star_id: int,
    data: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """在明星板块发布帖子（仅该明星的已通过粉丝可发帖）"""
    star = db.query(Star).filter(Star.id == star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    # 验证用户是否是该明星的已通过粉丝（管理员跳过）
    if not current_user.is_superuser:
        is_fan = db.query(StarFan).filter(
            StarFan.star_id == star_id,
            StarFan.user_id == current_user.id,
            StarFan.status == "approved"
        ).first()
        if not is_fan:
            raise HTTPException(
                status_code=403,
                detail="仅该明星的已通过粉丝可以发帖，请先申请成为粉丝"
            )

    # 创建帖子
    post = Post(
        title=data.title,
        content=data.content,
        content_format=getattr(data, 'content_format', 'markdown'),
        author_id=current_user.id,
        is_published=data.is_published,
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    # 关联到明星
    star_post = StarPost(star_id=star_id, post_id=post.id)
    db.add(star_post)

    # 更新明星帖子数
    star.post_count = db.query(func.count(StarPost.id)).filter(
        StarPost.star_id == star_id
    ).scalar() + 1

    db.commit()

    # 返回帖子（需要渲染内容）
    from app.utils.markdown_utils import render_content, generate_summary
    result = PostPublic.model_validate(post)
    result.content_html = render_content(post.content, post.content_format)
    result.content_summary = generate_summary(post.content, post.content_format, 200)
    return result


@router.get("/{star_id}/posts", response_model=List[PostPublic])
def list_star_posts(
    star_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取明星的帖子列表"""
    star = db.query(Star).filter(Star.id == star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    # 查询关联的帖子
    star_posts = db.query(StarPost).filter(
        StarPost.star_id == star_id
    ).order_by(StarPost.created_at.desc())\
     .offset((page - 1) * page_size)\
     .limit(page_size).all()

    if not star_posts:
        return []

    post_ids = [sp.post_id for sp in star_posts]
    posts = db.query(Post).filter(
        Post.id.in_(post_ids),
        Post.is_published == True,
        Post.status == "approved"
    ).order_by(Post.is_pinned.desc(), Post.created_at.desc()).all()

    # 构建 id -> post 映射
    post_map = {p.id: p for p in posts}

    # 按 star_posts 顺序返回，置顶帖优先
    from app.utils.markdown_utils import render_content, generate_summary
    result = []
    # 先添加置顶帖
    for sp in star_posts:
        post = post_map.get(sp.post_id)
        if post and post.is_pinned:
            item = PostPublic.model_validate(post)
            item.content_html = render_content(post.content, post.content_format)
            item.content_summary = generate_summary(post.content, post.content_format, 200)
            result.append(item)
    # 再添加普通帖
    for sp in star_posts:
        post = post_map.get(sp.post_id)
        if post and not post.is_pinned:
            item = PostPublic.model_validate(post)
            item.content_html = render_content(post.content, post.content_format)
            item.content_summary = generate_summary(post.content, post.content_format, 200)
            result.append(item)

    return result


# ─── 明星排行榜 ───

@router.get("/ranking/fans", response_model=List[StarRankingItem])
def ranking_by_fans(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """明星粉丝数排行榜"""
    stars = db.query(Star).filter(
        Star.is_active == True
    ).order_by(Star.fan_count.desc())\
     .limit(limit).all()

    return [
        StarRankingItem(
            rank=i + 1,
            star=StarPublic.model_validate(s),
            fan_count=s.fan_count,
            post_count=s.post_count,
            heat_score=s.heat_score
        )
        for i, s in enumerate(stars)
    ]


# ─── 粉丝功能（申请-审核制） ───

@router.post("/{star_id}/fans/apply", response_model=StarFanPublic, status_code=201)
def apply_to_be_fan(
    star_id: int,
    data: StarFanApplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """申请成为明星粉丝"""
    star = db.query(Star).filter(Star.id == star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    # 检查是否已申请或已是粉丝
    existing = db.query(StarFan).filter(
        StarFan.star_id == star_id,
        StarFan.user_id == current_user.id
    ).first()

    if existing:
        if existing.status == "approved":
            raise HTTPException(status_code=400, detail="您已经是该明星的粉丝")
        elif existing.status == "pending":
            raise HTTPException(status_code=400, detail="您的申请正在审核中")
        elif existing.status == "rejected":
            # 被拒绝后可以重新申请，更新状态为 pending
            existing.status = "pending"
            existing.apply_message = data.apply_message
            existing.created_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            result = StarFanPublic.model_validate(existing)
            result.user = UserPublic.model_validate(current_user)
            return result

    # 创建新申请
    fan = StarFan(
        star_id=star_id,
        user_id=current_user.id,
        status="pending",
        apply_message=data.apply_message
    )
    db.add(fan)
    db.commit()
    db.refresh(fan)

    result = StarFanPublic.model_validate(fan)
    result.user = UserPublic.model_validate(current_user)
    return result


@router.get("/{star_id}/fans/pending", response_model=StarFanList)
def list_pending_fan_applications(
    star_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取待审核的粉丝申请列表（仅明星管理员/群主）"""
    star = db.query(Star).filter(Star.id == star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    # 检查权限（仅管理员可审核）
    # 这里简化处理，实际应该检查用户是否是明星管理员
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅管理员可查看申请列表")

    query = db.query(StarFan).filter(
        StarFan.star_id == star_id,
        StarFan.status == "pending"
    )

    total = query.count()
    fans = query.order_by(StarFan.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    result = []
    for f in fans:
        item = StarFanPublic.model_validate(f)
        user = db.query(User).filter(User.id == f.user_id).first()
        if user:
            item.user = UserPublic.model_validate(user)
        result.append(item)

    return StarFanList(fans=result, total=total, page=page, page_size=page_size)


@router.post("/{star_id}/fans/{fan_id}/review", response_model=StarFanPublic)
def review_fan_application(
    star_id: int,
    fan_id: int,
    data: StarFanReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """审核粉丝申请（仅明星管理员）"""
    star = db.query(Star).filter(Star.id == star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    # 检查权限（仅管理员可审核）
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅管理员可审核粉丝申请")

    fan = db.query(StarFan).filter(
        StarFan.id == fan_id,
        StarFan.star_id == star_id
    ).first()

    if not fan:
        raise HTTPException(status_code=404, detail="申请记录不存在")

    if fan.status != "pending":
        raise HTTPException(status_code=400, detail="该申请已审核")

    fan.status = data.status
    if data.status == "approved":
        fan.fan_type = data.fan_type
        # 审核通过时自动创建/更新粉丝牌
        from app.routers.fan_badge_router import _get_or_create_badge
        _get_or_create_badge(fan.user_id, star_id, data.fan_type, db)
    fan.reviewed_by = current_user.id
    fan.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(fan)

    result = StarFanPublic.model_validate(fan)
    user = db.query(User).filter(User.id == fan.user_id).first()
    if user:
        result.user = UserPublic.model_validate(user)
    result.reviewer = UserPublic.model_validate(current_user)
    return result


@router.get("/{star_id}/fans", response_model=StarFanList)
def list_approved_fans(
    star_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取明星的粉丝列表（仅已通过审核的）"""
    star = db.query(Star).filter(Star.id == star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    query = db.query(StarFan).filter(
        StarFan.star_id == star_id,
        StarFan.status == "approved"
    )

    total = query.count()
    fans = query.order_by(StarFan.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    result = []
    for f in fans:
        item = StarFanPublic.model_validate(f)
        user = db.query(User).filter(User.id == f.user_id).first()
        if user:
            item.user = UserPublic.model_validate(user)
        result.append(item)

    return StarFanList(fans=result, total=total, page=page, page_size=page_size)


@router.get("/users/me/fan-applications", response_model=List[MyFanApplicationPublic])
def list_my_fan_applications(
    status: Optional[str] = Query(None, pattern="^(pending|approved|rejected)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取我的粉丝申请列表"""
    query = db.query(StarFan).filter(StarFan.user_id == current_user.id)

    if status:
        query = query.filter(StarFan.status == status)

    applications = query.order_by(StarFan.created_at.desc()).all()

    result = []
    for app in applications:
        item = MyFanApplicationPublic.model_validate(app)
        star = db.query(Star).filter(Star.id == app.star_id).first()
        if star:
            item.star = StarPublic.model_validate(star)
        result.append(item)
    return result


@router.delete("/{star_id}/fans/me", response_model=Msg)
def cancel_fan_application(
    star_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """取消粉丝申请或退出粉丝"""
    fan = db.query(StarFan).filter(
        StarFan.star_id == star_id,
        StarFan.user_id == current_user.id
    ).first()

    if not fan:
        raise HTTPException(status_code=404, detail="您没有申请记录")

    db.delete(fan)
    db.commit()
    return Msg(msg="已取消粉丝身份")


@router.patch("/{star_id}/fans/{fan_id}/type", response_model=StarFanPublic)
def update_fan_type(
    star_id: int,
    fan_id: int,
    fan_type: str = Query(..., pattern="^(casual|true_fan|diehard)$", description="粉丝类型"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """升级/修改粉丝类型（仅管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅管理员可修改粉丝类型")

    fan = db.query(StarFan).filter(
        StarFan.id == fan_id,
        StarFan.star_id == star_id,
        StarFan.status == "approved"
    ).first()

    if not fan:
        raise HTTPException(status_code=404, detail="粉丝记录不存在")

    fan.fan_type = fan_type
    db.commit()
    db.refresh(fan)

    result = StarFanPublic.model_validate(fan)
    user = db.query(User).filter(User.id == fan.user_id).first()
    if user:
        result.user = UserPublic.model_validate(user)
    return result


# ─── 粉丝功能 ───

@router.post("/{star_id}/follow", response_model=StarFollowResponse)
def toggle_follow_star(
    star_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    关注/取消关注明星
    - 已关注则取消，未关注则添加
    """
    star = db.query(Star).filter(Star.id == star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    # 检查是否已关注
    existing = db.query(StarFollow).filter(
        StarFollow.star_id == star_id,
        StarFollow.user_id == current_user.id
    ).first()

    if existing:
        # 已关注 → 取消关注
        db.delete(existing)
        db.commit()
        is_following = False
        msg = "已取消关注"
    else:
        # 未关注 → 添加关注
        follow = StarFollow(star_id=star_id, user_id=current_user.id)
        db.add(follow)
        db.commit()
        is_following = True
        msg = "已关注"

    # 更新明星粉丝数
    fan_count = db.query(func.count(StarFollow.id)).filter(
        StarFollow.star_id == star_id
    ).scalar()
    star.fan_count = fan_count
    db.commit()

    return StarFollowResponse(
        msg=msg,
        is_following=is_following,
        fan_count=fan_count
    )


@router.get("/{star_id}/followers", response_model=List[StarFollowerPublic])
def list_star_followers(
    star_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取明星的粉丝列表"""
    star = db.query(Star).filter(Star.id == star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    followers = db.query(StarFollow).filter(
        StarFollow.star_id == star_id
    ).order_by(StarFollow.created_at.desc())\
     .offset((page - 1) * page_size)\
     .limit(page_size).all()

    result = []
    for f in followers:
        item = StarFollowerPublic.model_validate(f)
        user = db.query(User).filter(User.id == f.user_id).first()
        if user:
            item.user = UserPublic.model_validate(user)
        result.append(item)
    return result


@router.get("/{star_id}/follow/status", response_model=dict)
def check_follow_status(
    star_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """检查当前用户是否关注了该明星"""
    star = db.query(Star).filter(Star.id == star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    is_following = db.query(StarFollow).filter(
        StarFollow.star_id == star_id,
        StarFollow.user_id == current_user.id
    ).first() is not None

    return {"is_following": is_following}


@router.get("/users/me/following", response_model=List[UserFollowingStarPublic])
def list_my_following_stars(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取我关注的明星列表"""
    following = db.query(StarFollow).filter(
        StarFollow.user_id == current_user.id
    ).order_by(StarFollow.created_at.desc())\
     .offset((page - 1) * page_size)\
     .limit(page_size).all()

    result = []
    for f in following:
        item = UserFollowingStarPublic.model_validate(f)
        star = db.query(Star).filter(Star.id == f.star_id).first()
        if star:
            item.star = StarPublic.model_validate(star)
        result.append(item)
    return result


@router.get("/ranking/heat", response_model=List[StarRankingItem])
def ranking_by_heat(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """明星热度排行榜"""
    stars = db.query(Star).filter(
        Star.is_active == True
    ).order_by(Star.heat_score.desc())\
     .limit(limit).all()

    return [
        StarRankingItem(
            rank=i + 1,
            star=StarPublic.model_validate(s),
            fan_count=s.fan_count,
            post_count=s.post_count,
            heat_score=s.heat_score
        )
        for i, s in enumerate(stars)
    ]


@router.get("/ranking/posts", response_model=List[StarRankingItem])
def ranking_by_posts(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """明星帖子数排行榜"""
    stars = db.query(Star).filter(
        Star.is_active == True
    ).order_by(Star.post_count.desc())\
     .limit(limit).all()

    return [
        StarRankingItem(
            rank=i + 1,
            star=StarPublic.model_validate(s),
            fan_count=s.fan_count,
            post_count=s.post_count,
            heat_score=s.heat_score
        )
        for i, s in enumerate(stars)
    ]
