"""
粉丝牌模块路由

粉丝可以在个人主页展示至多一个明星的粉丝牌/粉丝称号
根据粉丝的等级（路人粉/真爱粉/死忠粉）对应不同的粉丝牌、称号
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from app.database import get_db
from app.models import User, Star, StarFan, FanBadge
from app.schemas import (
    FanBadgePublic, FanBadgeList, FanBadgeSetDisplayRequest,
    BADGE_CONFIG, Msg, UserPublic
)
from app.auth import get_current_active_user
from app.logging_config import logger

router = APIRouter(prefix="/fan-badges", tags=["粉丝牌"])


def _get_or_create_badge(user_id: int, star_id: int, fan_type: str, db: Session) -> FanBadge:
    """获取或创建粉丝牌"""
    badge = db.query(FanBadge).filter(
        FanBadge.user_id == user_id,
        FanBadge.star_id == star_id
    ).first()

    if not badge:
        star = db.query(Star).filter(Star.id == star_id).first()
        if not star:
            raise HTTPException(status_code=404, detail="明星不存在")

        config = BADGE_CONFIG.get(fan_type, BADGE_CONFIG["casual"])
        badge_name = config["badge_name_template"].format(star_name=star.name)

        badge = FanBadge(
            user_id=user_id,
            star_id=star_id,
            fan_type=fan_type,
            badge_name=badge_name,
            badge_level=config["level"],
            badge_color=config["color"],
            is_displayed=False
        )
        db.add(badge)
        db.commit()
        db.refresh(badge)
    else:
        # 如果粉丝类型变化，更新粉丝牌
        if badge.fan_type != fan_type:
            config = BADGE_CONFIG.get(fan_type, BADGE_CONFIG["casual"])
            star = db.query(Star).filter(Star.id == star_id).first()
            badge.fan_type = fan_type
            badge.badge_name = config["badge_name_template"].format(star_name=star.name if star else "")
            badge.badge_level = config["level"]
            badge.badge_color = config["color"]
            db.commit()
            db.refresh(badge)

    return badge


def _clear_other_displayed_badges(user_id: int, except_badge_id: int, db: Session):
    """清除其他已展示的粉丝牌（确保只展示一个）"""
    db.query(FanBadge).filter(
        FanBadge.user_id == user_id,
        FanBadge.id != except_badge_id,
        FanBadge.is_displayed == True
    ).update({"is_displayed": False})
    db.commit()


# ─── 粉丝牌管理 ───

@router.get("/my", response_model=FanBadgeList)
def list_my_badges(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取我的所有粉丝牌"""
    query = db.query(FanBadge).filter(FanBadge.user_id == current_user.id)

    total = query.count()
    badges = query.order_by(FanBadge.is_displayed.desc(), FanBadge.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    result = []
    for b in badges:
        item = FanBadgePublic.model_validate(b)
        star = db.query(Star).filter(Star.id == b.star_id).first()
        if star:
            from app.schemas import StarPublic
            item.star = StarPublic.model_validate(star)
        result.append(item)

    return FanBadgeList(badges=result, total=total, page=page, page_size=page_size)


@router.get("/my/displayed", response_model=FanBadgePublic)
def get_my_displayed_badge(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取我当前展示的粉丝牌"""
    badge = db.query(FanBadge).filter(
        FanBadge.user_id == current_user.id,
        FanBadge.is_displayed == True
    ).first()

    if not badge:
        raise HTTPException(status_code=404, detail="未设置展示的粉丝牌")

    result = FanBadgePublic.model_validate(badge)
    star = db.query(Star).filter(Star.id == badge.star_id).first()
    if star:
        from app.schemas import StarPublic
        result.star = StarPublic.model_validate(star)
    return result


@router.post("/my/display", response_model=Msg)
def set_display_badge(
    data: FanBadgeSetDisplayRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """设置要展示的粉丝牌（每人最多展示一个）"""
    badge = db.query(FanBadge).filter(
        FanBadge.id == data.badge_id,
        FanBadge.user_id == current_user.id
    ).first()

    if not badge:
        raise HTTPException(status_code=404, detail="粉丝牌不存在或不属于您")

    # 清除其他已展示的粉丝牌
    _clear_other_displayed_badges(current_user.id, badge.id, db)

    # 设置当前粉丝牌为展示
    badge.is_displayed = True
    db.commit()

    return Msg(msg="已设置展示的粉丝牌")


@router.delete("/my/display", response_model=Msg)
def clear_display_badge(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """取消展示粉丝牌"""
    db.query(FanBadge).filter(
        FanBadge.user_id == current_user.id,
        FanBadge.is_displayed == True
    ).update({"is_displayed": False})
    db.commit()

    return Msg(msg="已取消展示粉丝牌")


# ─── 查看他人粉丝牌 ───

@router.get("/user/{user_id}", response_model=FanBadgePublic)
def get_user_displayed_badge(
    user_id: int,
    db: Session = Depends(get_db)
):
    """查看用户展示的粉丝牌（公开）"""
    badge = db.query(FanBadge).filter(
        FanBadge.user_id == user_id,
        FanBadge.is_displayed == True
    ).first()

    if not badge:
        raise HTTPException(status_code=404, detail="该用户未设置展示的粉丝牌")

    result = FanBadgePublic.model_validate(badge)
    star = db.query(Star).filter(Star.id == badge.star_id).first()
    if star:
        from app.schemas import StarPublic
        result.star = StarPublic.model_validate(star)
    return result


@router.get("/user/{user_id}/all", response_model=FanBadgeList)
def list_user_badges(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """查看用户的所有粉丝牌（公开，仅展示已设置为展示的）"""
    query = db.query(FanBadge).filter(
        FanBadge.user_id == user_id,
        FanBadge.is_displayed == True
    )

    total = query.count()
    badges = query.order_by(FanBadge.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    result = []
    for b in badges:
        item = FanBadgePublic.model_validate(b)
        star = db.query(Star).filter(Star.id == b.star_id).first()
        if star:
            from app.schemas import StarPublic
            item.star = StarPublic.model_validate(star)
        result.append(item)

    return FanBadgeList(badges=result, total=total, page=page, page_size=page_size)


# ─── 粉丝牌配置 ───

@router.get("/config", response_model=dict)
def get_badge_config():
    """获取粉丝牌配置（称号、颜色对应关系）"""
    return BADGE_CONFIG
