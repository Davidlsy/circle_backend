"""
粉丝圈模块路由

一个明星对应一个粉丝圈，粉丝圈整合：
- 粉丝管理
- 风纪委员会
- 帖子板块
- 群聊
- 签到
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from app.database import get_db
from app.models import User, Star, StarFan, FanCircle, DisciplineCommittee, FanCheckIn
from app.schemas import (
    FanCirclePublic, FanCircleDetail, FanCircleList,
    FanCircleCreate, FanCircleUpdate, Msg, UserPublic
)
from app.auth import get_current_active_user
from app.logging_config import logger

router = APIRouter(prefix="/fan-circles", tags=["粉丝圈"])


def _get_or_create_fan_circle(star_id: int, db: Session) -> FanCircle:
    """获取或创建粉丝圈"""
    circle = db.query(FanCircle).filter(FanCircle.star_id == star_id).first()
    if not circle:
        star = db.query(Star).filter(Star.id == star_id).first()
        if not star:
            raise HTTPException(status_code=404, detail="明星不存在")
        circle = FanCircle(
            star_id=star_id,
            name=f"{star.name}粉丝圈",
            description=f"欢迎来到{star.name}的粉丝圈"
        )
        db.add(circle)
        db.commit()
        db.refresh(circle)
    return circle


def _update_fan_circle_stats(circle_id: int, db: Session):
    """更新粉丝圈统计"""
    circle = db.query(FanCircle).filter(FanCircle.id == circle_id).first()
    if circle:
        # 更新成员数
        circle.member_count = db.query(func.count(StarFan.id)).filter(
            StarFan.star_id == circle.star_id,
            StarFan.status == "approved"
        ).scalar() or 0
        # 更新帖子数
        from app.models import StarPost
        circle.post_count = db.query(func.count(StarPost.id)).filter(
            StarPost.star_id == circle.star_id
        ).scalar() or 0
        db.commit()


# ─── 粉丝圈基础 ───

@router.get("/", response_model=FanCircleList)
def list_fan_circles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取粉丝圈列表"""
    query = db.query(FanCircle).filter(FanCircle.status == "active")

    total = query.count()
    circles = query.order_by(FanCircle.member_count.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    return FanCircleList(
        circles=[FanCirclePublic.model_validate(c) for c in circles],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{circle_id}", response_model=FanCircleDetail)
def get_fan_circle(
    circle_id: int,
    db: Session = Depends(get_db)
):
    """获取粉丝圈详情"""
    circle = db.query(FanCircle).filter(
        FanCircle.id == circle_id,
        FanCircle.status == "active"
    ).first()
    if not circle:
        raise HTTPException(status_code=404, detail="粉丝圈不存在")

    # 更新统计
    _update_fan_circle_stats(circle_id, db)
    db.refresh(circle)

    result = FanCircleDetail.model_validate(circle)
    result.star = circle.star
    return result


@router.get("/by-star/{star_id}", response_model=FanCircleDetail)
def get_fan_circle_by_star(
    star_id: int,
    db: Session = Depends(get_db)
):
    """通过明星ID获取粉丝圈"""
    circle = db.query(FanCircle).filter(
        FanCircle.star_id == star_id,
        FanCircle.status == "active"
    ).first()
    if not circle:
        # 自动创建
        circle = _get_or_create_fan_circle(star_id, db)

    _update_fan_circle_stats(circle.id, db)
    db.refresh(circle)

    result = FanCircleDetail.model_validate(circle)
    result.star = circle.star
    return result


@router.put("/{circle_id}", response_model=FanCirclePublic)
def update_fan_circle(
    circle_id: int,
    data: FanCircleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """更新粉丝圈信息（仅管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅管理员可修改")

    circle = db.query(FanCircle).filter(FanCircle.id == circle_id).first()
    if not circle:
        raise HTTPException(status_code=404, detail="粉丝圈不存在")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(circle, field, value)

    db.commit()
    db.refresh(circle)
    return FanCirclePublic.model_validate(circle)


# ─── 粉丝圈成员 ───

@router.get("/{circle_id}/members", response_model=dict)
def list_circle_members(
    circle_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    fan_type: Optional[str] = Query(None, pattern="^(casual|true_fan|diehard)$"),
    db: Session = Depends(get_db)
):
    """获取粉丝圈成员列表"""
    circle = db.query(FanCircle).filter(FanCircle.id == circle_id).first()
    if not circle:
        raise HTTPException(status_code=404, detail="粉丝圈不存在")

    query = db.query(StarFan).filter(
        StarFan.star_id == circle.star_id,
        StarFan.status == "approved"
    )

    if fan_type:
        query = query.filter(StarFan.fan_type == fan_type)

    total = query.count()
    fans = query.order_by(StarFan.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    members = []
    for f in fans:
        user = db.query(User).filter(User.id == f.user_id).first()
        if user:
            members.append({
                "id": f.id,
                "user_id": f.user_id,
                "user": UserPublic.model_validate(user),
                "fan_type": f.fan_type,
                "created_at": f.created_at.isoformat() if f.created_at else None
            })

    return {"members": members, "total": total, "page": page, "page_size": page_size}


@router.get("/{circle_id}/members/count", response_model=dict)
def get_member_stats(
    circle_id: int,
    db: Session = Depends(get_db)
):
    """获取粉丝圈成员统计"""
    circle = db.query(FanCircle).filter(FanCircle.id == circle_id).first()
    if not circle:
        raise HTTPException(status_code=404, detail="粉丝圈不存在")

    stats = db.query(
        StarFan.fan_type,
        func.count(StarFan.id).label("count")
    ).filter(
        StarFan.star_id == circle.star_id,
        StarFan.status == "approved"
    ).group_by(StarFan.fan_type).all()

    result = {s.fan_type: s.count for s in stats}
    result["total"] = sum(result.values())
    return result


# ─── 粉丝圈概览 ───

@router.get("/{circle_id}/overview", response_model=dict)
def get_circle_overview(
    circle_id: int,
    db: Session = Depends(get_db)
):
    """获取粉丝圈完整概览（粉丝、风纪委、帖子、签到统计）"""
    circle = db.query(FanCircle).filter(
        FanCircle.id == circle_id,
        FanCircle.status == "active"
    ).first()
    if not circle:
        raise HTTPException(status_code=404, detail="粉丝圈不存在")

    # 更新统计
    _update_fan_circle_stats(circle_id, db)

    # 风纪委员会成员数
    committee_count = db.query(func.count(DisciplineCommittee.id)).filter(
        DisciplineCommittee.star_id == circle.star_id,
        DisciplineCommittee.status == "approved"
    ).scalar() or 0

    # 今日签到数
    from datetime import date
    today = date.today()
    today_checkin_count = db.query(func.count(FanCheckIn.id)).filter(
        FanCheckIn.star_id == circle.star_id,
        FanCheckIn.checkin_date == today
    ).scalar() or 0

    # 最新帖子
    from app.models import StarPost, Post
    latest_posts = db.query(Post).join(StarPost).filter(
        StarPost.star_id == circle.star_id,
        Post.status == "approved"
    ).order_by(Post.created_at.desc()).limit(5).all()

    return {
        "circle": FanCirclePublic.model_validate(circle),
        "stats": {
            "member_count": circle.member_count,
            "post_count": circle.post_count,
            "committee_count": committee_count,
            "today_checkin_count": today_checkin_count
        },
        "latest_posts": [
            {"id": p.id, "title": p.title, "created_at": p.created_at.isoformat()}
            for p in latest_posts
        ]
    }


# ─── 我的粉丝圈 ───

@router.get("/users/me/joined", response_model=dict)
def list_my_fan_circles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取我加入的粉丝圈列表（含我在每个圈的粉丝类型和签到状态）"""
    # 查询我是粉丝的明星
    my_fans = db.query(StarFan).filter(
        StarFan.user_id == current_user.id,
        StarFan.status == "approved"
    ).all()

    star_ids = [f.star_id for f in my_fans]
    if not star_ids:
        return {"circles": [], "total": 0, "page": page, "page_size": page_size}

    # 构建 star_id -> fan_type 映射
    fan_type_map = {f.star_id: f.fan_type for f in my_fans}

    query = db.query(FanCircle).filter(
        FanCircle.star_id.in_(star_ids),
        FanCircle.status == "active"
    )

    total = query.count()
    circles = query.order_by(FanCircle.member_count.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    from datetime import date
    today = date.today()

    circle_list = []
    for c in circles:
        # 查询今日签到状态
        from app.models import FanCheckIn
        today_checkin = db.query(FanCheckIn).filter(
            FanCheckIn.star_id == c.star_id,
            FanCheckIn.user_id == current_user.id,
            FanCheckIn.checkin_date == today
        ).first()

        # 查询是否是风纪委员
        is_committee = db.query(DisciplineCommittee).filter(
            DisciplineCommittee.star_id == c.star_id,
            DisciplineCommittee.user_id == current_user.id,
            DisciplineCommittee.status == "approved"
        ).first() is not None

        item = FanCirclePublic.model_validate(c)
        circle_list.append({
            "circle": item,
            "my_fan_type": fan_type_map.get(c.star_id, "casual"),
            "today_checked_in": today_checkin is not None,
            "is_committee_member": is_committee,
            "joined_at": None  # 可从 StarFan 获取
        })

    return {"circles": circle_list, "total": total, "page": page, "page_size": page_size}


@router.get("/users/me/summary", response_model=dict)
def get_my_fan_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取我的粉丝总览（加入了多少粉丝圈、各类型统计、今日签到情况）"""
    # 我加入的粉丝圈数
    my_fans = db.query(StarFan).filter(
        StarFan.user_id == current_user.id,
        StarFan.status == "approved"
    ).all()

    total_circles = len(my_fans)

    # 按粉丝类型统计
    fan_type_counts = {}
    for f in my_fans:
        fan_type_counts[f.fan_type] = fan_type_counts.get(f.fan_type, 0) + 1

    # 今日签到统计
    from datetime import date
    from app.models import FanCheckIn
    today = date.today()
    today_checkins = db.query(FanCheckIn).filter(
        FanCheckIn.user_id == current_user.id,
        FanCheckIn.checkin_date == today
    ).all()
    today_checkin_count = len(today_checkins)
    checked_circle_ids = [c.star_id for c in today_checkins]

    # 风纪委员身份统计
    committee_count = db.query(DisciplineCommittee).filter(
        DisciplineCommittee.user_id == current_user.id,
        DisciplineCommittee.status == "approved"
    ).count()

    # 累计积分
    total_points = db.query(func.sum(FanCheckIn.points)).filter(
        FanCheckIn.user_id == current_user.id
    ).scalar() or 0

    return {
        "total_circles_joined": total_circles,
        "fan_type_distribution": fan_type_counts,
        "today_checkin_count": today_checkin_count,
        "today_checkin_total": total_circles,
        "committee_count": committee_count,
        "total_checkin_points": total_points,
        "circle_details": [
            {
                "star_id": f.star_id,
                "fan_type": f.fan_type,
                "today_checked_in": f.star_id in checked_circle_ids
            }
            for f in my_fans
        ]
    }
