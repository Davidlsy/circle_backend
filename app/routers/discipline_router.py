"""
风纪委员会模块路由

风纪委员会是粉丝模块内部的审核组织，成员负责审核该明星板块下的帖子。
成为风纪委员需要先成为粉丝，然后申请并经过审核。
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional

from app.database import get_db
from app.models import (
    User, Star, StarFan, DisciplineCommittee, Post, StarPost
)
from app.schemas import (
    DCApplyRequest, DCReviewRequest, DCPublic, DCList,
    MyDCApplicationPublic, Msg, UserPublic, StarPublic
)
from app.auth import get_current_active_user
from app.logging_config import logger

router = APIRouter(prefix="/stars", tags=["风纪委员会"])


def _is_approved_fan(star_id: int, user_id: int, db: Session) -> bool:
    """检查用户是否是该明星的已通过粉丝"""
    fan = db.query(StarFan).filter(
        StarFan.star_id == star_id,
        StarFan.user_id == user_id,
        StarFan.status == "approved"
    ).first()
    return fan is not None


def _is_committee_member(star_id: int, user_id: int, db: Session) -> Optional[str]:
    """检查用户是否是风纪委员，返回角色或 None"""
    member = db.query(DisciplineCommittee).filter(
        DisciplineCommittee.star_id == star_id,
        DisciplineCommittee.user_id == user_id,
        DisciplineCommittee.status == "approved"
    ).first()
    return member.role if member else None


# ─── 风纪委员会申请 ───

@router.post("/{star_id}/committee/apply", response_model=DCPublic, status_code=201)
def apply_to_committee(
    star_id: int,
    data: DCApplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """申请加入风纪委员会（需先成为已通过的粉丝）"""
    star = db.query(Star).filter(Star.id == star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    # 前置条件：必须是已通过的粉丝
    if not _is_approved_fan(star_id, current_user.id, db):
        raise HTTPException(status_code=403, detail="仅已通过的粉丝可申请加入风纪委员会")

    # 检查是否已申请
    existing = db.query(DisciplineCommittee).filter(
        DisciplineCommittee.star_id == star_id,
        DisciplineCommittee.user_id == current_user.id
    ).first()

    if existing:
        if existing.status == "approved":
            raise HTTPException(status_code=400, detail="您已经是风纪委员会成员")
        elif existing.status == "pending":
            raise HTTPException(status_code=400, detail="您的申请正在审核中")
        elif existing.status == "rejected":
            # 被拒绝后可重新申请
            existing.status = "pending"
            existing.apply_message = data.apply_message
            existing.created_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            result = DCPublic.model_validate(existing)
            result.user = UserPublic.model_validate(current_user)
            return result
        elif existing.status == "resigned":
            # 辞职后可重新申请
            existing.status = "pending"
            existing.apply_message = data.apply_message
            existing.created_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            result = DCPublic.model_validate(existing)
            result.user = UserPublic.model_validate(current_user)
            return result

    # 创建新申请
    application = DisciplineCommittee(
        star_id=star_id,
        user_id=current_user.id,
        status="pending",
        role="member",
        apply_message=data.apply_message
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    result = DCPublic.model_validate(application)
    result.user = UserPublic.model_validate(current_user)
    return result


# ─── 风纪委员会管理 ───

@router.get("/{star_id}/committee/pending", response_model=DCList)
def list_pending_applications(
    star_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取待审核的风纪委员会申请（仅管理员/委员长）"""
    star = db.query(Star).filter(Star.id == star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    # 权限检查：管理员 或 该明星的委员长
    role = _is_committee_member(star_id, current_user.id, db)
    if not current_user.is_superuser and role != "chairman":
        raise HTTPException(status_code=403, detail="仅管理员或委员长可查看申请")

    query = db.query(DisciplineCommittee).filter(
        DisciplineCommittee.star_id == star_id,
        DisciplineCommittee.status == "pending"
    )

    total = query.count()
    applications = query.order_by(DisciplineCommittee.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    result = []
    for a in applications:
        item = DCPublic.model_validate(a)
        user = db.query(User).filter(User.id == a.user_id).first()
        if user:
            item.user = UserPublic.model_validate(user)
        result.append(item)

    return DCList(members=result, total=total, page=page, page_size=page_size)


@router.post("/{star_id}/committee/{app_id}/review", response_model=DCPublic)
def review_committee_application(
    star_id: int,
    app_id: int,
    data: DCReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """审核风纪委员会申请（仅管理员/委员长）"""
    star = db.query(Star).filter(Star.id == star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    role = _is_committee_member(star_id, current_user.id, db)
    if not current_user.is_superuser and role != "chairman":
        raise HTTPException(status_code=403, detail="仅管理员或委员长可审核申请")

    application = db.query(DisciplineCommittee).filter(
        DisciplineCommittee.id == app_id,
        DisciplineCommittee.star_id == star_id
    ).first()

    if not application:
        raise HTTPException(status_code=404, detail="申请记录不存在")

    if application.status != "pending":
        raise HTTPException(status_code=400, detail="该申请已审核")

    application.status = data.status
    application.role = data.role if data.status == "approved" else "member"
    application.reviewed_by = current_user.id
    application.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(application)

    result = DCPublic.model_validate(application)
    user = db.query(User).filter(User.id == application.user_id).first()
    if user:
        result.user = UserPublic.model_validate(user)
    result.reviewer = UserPublic.model_validate(current_user)
    return result


@router.get("/{star_id}/committee", response_model=DCList)
def list_committee_members(
    star_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取风纪委员会成员列表（仅已通过的）"""
    star = db.query(Star).filter(Star.id == star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    query = db.query(DisciplineCommittee).filter(
        DisciplineCommittee.star_id == star_id,
        DisciplineCommittee.status == "approved"
    )

    total = query.count()
    members = query.order_by(
        # chairman 排在前面
        func.case((DisciplineCommittee.role == "chairman", 0), else_=1),
        DisciplineCommittee.created_at
    ).offset((page - 1) * page_size)\
     .limit(page_size).all()

    result = []
    for m in members:
        item = DCPublic.model_validate(m)
        user = db.query(User).filter(User.id == m.user_id).first()
        if user:
            item.user = UserPublic.model_validate(user)
        result.append(item)

    return DCList(members=result, total=total, page=page, page_size=page_size)


@router.get("/users/me/committee-applications", response_model=List[MyDCApplicationPublic])
def list_my_committee_applications(
    status: Optional[str] = Query(None, pattern="^(pending|approved|rejected|resigned)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取我的风纪委员会申请列表"""
    query = db.query(DisciplineCommittee).filter(
        DisciplineCommittee.user_id == current_user.id
    )

    if status:
        query = query.filter(DisciplineCommittee.status == status)

    applications = query.order_by(DisciplineCommittee.created_at.desc()).all()

    result = []
    for app in applications:
        item = MyDCApplicationPublic.model_validate(app)
        star = db.query(Star).filter(Star.id == app.star_id).first()
        if star:
            item.star = StarPublic.model_validate(star)
        result.append(item)
    return result


@router.delete("/{star_id}/committee/me", response_model=Msg)
def resign_from_committee(
    star_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """辞去风纪委员会职务"""
    member = db.query(DisciplineCommittee).filter(
        DisciplineCommittee.star_id == star_id,
        DisciplineCommittee.user_id == current_user.id,
        DisciplineCommittee.status == "approved"
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="您不是风纪委员会成员")

    member.status = "resigned"
    db.commit()
    return Msg(msg="已辞去风纪委员会职务")


# ─── 风纪委员审核帖子 ───

@router.post("/{star_id}/committee/posts/{post_id}/audit", response_model=Msg)
def audit_post_by_committee(
    star_id: int,
    post_id: int,
    action: str = Query(..., pattern="^(approve|reject)$"),
    reason: Optional[str] = Query(None, max_length=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """风纪委员审核帖子（仅风纪委员可操作）"""
    # 检查是否是风纪委员
    role = _is_committee_member(star_id, current_user.id, db)
    if not role:
        raise HTTPException(status_code=403, detail="仅风纪委员会成员可审核帖子")

    # 检查帖子是否属于该明星
    star_post = db.query(StarPost).filter(
        StarPost.star_id == star_id,
        StarPost.post_id == post_id
    ).first()

    if not star_post:
        raise HTTPException(status_code=404, detail="该帖子不属于此明星板块")

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    if post.status != "pending":
        raise HTTPException(status_code=400, detail="该帖子已审核")

    if action == "approve":
        post.status = "approved"
        msg = "帖子已通过审核"
    else:
        post.status = "rejected"
        msg = "帖子已驳回"

    db.commit()
    return Msg(msg=msg)


@router.get("/{star_id}/committee/posts/pending", response_model=dict)
def list_pending_posts_for_committee(
    star_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取待审核帖子列表（仅风纪委员可查看）"""
    role = _is_committee_member(star_id, current_user.id, db)
    if not role:
        raise HTTPException(status_code=403, detail="仅风纪委员会成员可查看")

    # 查询该明星下待审核的帖子
    pending_star_posts = db.query(StarPost).filter(
        StarPost.star_id == star_id
    ).all()
    pending_post_ids = [sp.post_id for sp in pending_star_posts]

    if not pending_post_ids:
        return {"posts": [], "total": 0, "page": page, "page_size": page_size}

    query = db.query(Post).filter(
        Post.id.in_(pending_post_ids),
        Post.status == "pending"
    )

    total = query.count()
    posts = query.order_by(Post.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    from app.utils.markdown_utils import generate_summary

    post_list = []
    for p in posts:
        author = db.query(User).filter(User.id == p.author_id).first()
        post_list.append({
            "id": p.id,
            "title": p.title,
            "content_summary": generate_summary(p.content, p.content_format, 100),
            "author_id": p.author_id,
            "author_name": author.username if author else "未知",
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })

    return {"posts": post_list, "total": total, "page": page, "page_size": page_size}
