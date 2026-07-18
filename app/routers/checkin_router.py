"""
粉丝每日签到模块路由

签到时间窗口：当日 04:00 至次日 04:00
"""
from datetime import datetime, date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from app.database import get_db
from app.models import User, Star, StarFan, FanCheckIn
from app.schemas import (
    FanCheckInResponse, FanCheckInPublic, FanCheckInStats,
    FanCheckInRankItem, FanCheckInCalendar, UserPublic, Msg
)
from app.auth import get_current_active_user
from app.logging_config import logger

router = APIRouter(prefix="/stars", tags=["粉丝签到"])


def _get_checkin_date(current_time: datetime) -> date:
    """
    根据当前时间计算签到日期
    04:00-23:59:59 算当天
    00:00-03:59:59 算前一天
    """
    if current_time.hour < 4:
        # 凌晨 0-3 点，算前一天
        return (current_time - timedelta(days=1)).date()
    else:
        # 4 点及以后，算当天
        return current_time.date()


def _has_checked_in_today(star_id: int, user_id: int, db: Session) -> Optional[FanCheckIn]:
    """检查用户今日是否已签到"""
    today = _get_checkin_date(datetime.utcnow())
    return db.query(FanCheckIn).filter(
        FanCheckIn.star_id == star_id,
        FanCheckIn.user_id == user_id,
        FanCheckIn.checkin_date == today
    ).first()


def _get_consecutive_days(star_id: int, user_id: int, today: date, db: Session) -> int:
    """计算连续签到天数"""
    consecutive = 1
    check_date = today - timedelta(days=1)

    while True:
        record = db.query(FanCheckIn).filter(
            FanCheckIn.star_id == star_id,
            FanCheckIn.user_id == user_id,
            FanCheckIn.checkin_date == check_date
        ).first()
        if record:
            consecutive += 1
            check_date -= timedelta(days=1)
        else:
            break

    return consecutive


# ─── 签到功能 ───

@router.post("/{star_id}/checkin", response_model=FanCheckInResponse)
def check_in(
    star_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """粉丝每日签到（04:00-次日04:00）"""
    # 验证明星
    star = db.query(Star).filter(Star.id == star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    # 验证用户是否是已通过的粉丝
    is_fan = db.query(StarFan).filter(
        StarFan.star_id == star_id,
        StarFan.user_id == current_user.id,
        StarFan.status == "approved"
    ).first()
    if not is_fan:
        raise HTTPException(status_code=403, detail="仅已通过的粉丝可以签到")

    # 检查今日是否已签到
    today = _get_checkin_date(datetime.utcnow())
    existing = _has_checked_in_today(star_id, current_user.id, db)
    if existing:
        raise HTTPException(status_code=400, detail="今日已签到，请明天再来")

    # 计算连续签到天数
    consecutive_days = _get_consecutive_days(star_id, current_user.id, today, db)

    # 计算积分（连续签到奖励）
    points = 1
    if consecutive_days >= 30:
        points = 5
    elif consecutive_days >= 7:
        points = 3
    elif consecutive_days >= 3:
        points = 2

    # 创建签到记录
    checkin = FanCheckIn(
        star_id=star_id,
        user_id=current_user.id,
        checkin_date=today,
        checkin_time=datetime.utcnow(),
        consecutive_days=consecutive_days,
        points=points
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)

    # 统计累计签到天数
    total_days = db.query(func.count(FanCheckIn.id)).filter(
        FanCheckIn.star_id == star_id,
        FanCheckIn.user_id == current_user.id
    ).scalar()

    return FanCheckInResponse(
        msg="签到成功！",
        checkin=FanCheckInPublic.model_validate(checkin),
        total_days=total_days,
        consecutive_days=consecutive_days,
        today_points=points
    )


@router.get("/{star_id}/checkin/status", response_model=FanCheckInStats)
def get_checkin_status(
    star_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取我的签到统计"""
    star = db.query(Star).filter(Star.id == star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    # 检查是否是粉丝
    is_fan = db.query(StarFan).filter(
        StarFan.star_id == star_id,
        StarFan.user_id == current_user.id,
        StarFan.status == "approved"
    ).first()
    if not is_fan:
        raise HTTPException(status_code=403, detail="仅已通过的粉丝可以查看")

    today = _get_checkin_date(datetime.utcnow())

    # 今日签到状态
    today_checkin = db.query(FanCheckIn).filter(
        FanCheckIn.star_id == star_id,
        FanCheckIn.user_id == current_user.id,
        FanCheckIn.checkin_date == today
    ).first()

    # 累计签到天数
    total_days = db.query(func.count(FanCheckIn.id)).filter(
        FanCheckIn.star_id == star_id,
        FanCheckIn.user_id == current_user.id
    ).scalar()

    # 累计积分
    total_points = db.query(func.sum(FanCheckIn.points)).filter(
        FanCheckIn.star_id == star_id,
        FanCheckIn.user_id == current_user.id
    ).scalar() or 0

    # 连续签到天数（如果今日已签到，取今日记录；否则重新计算）
    consecutive_days = 0
    if today_checkin:
        consecutive_days = today_checkin.consecutive_days
    else:
        consecutive_days = _get_consecutive_days(star_id, current_user.id, today, db) - 1
        if consecutive_days < 0:
            consecutive_days = 0

    return FanCheckInStats(
        total_days=total_days,
        consecutive_days=consecutive_days,
        total_points=total_points,
        today_checked=today_checkin is not None,
        today_checkin_time=today_checkin.checkin_time if today_checkin else None
    )


@router.get("/{star_id}/checkin/calendar", response_model=FanCheckInCalendar)
def get_checkin_calendar(
    star_id: int,
    year: int = Query(datetime.utcnow().year, ge=2020, le=2100),
    month: int = Query(datetime.utcnow().month, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取签到日历（某月已签到日期）"""
    star = db.query(Star).filter(Star.id == star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    is_fan = db.query(StarFan).filter(
        StarFan.star_id == star_id,
        StarFan.user_id == current_user.id,
        StarFan.status == "approved"
    ).first()
    if not is_fan:
        raise HTTPException(status_code=403, detail="仅已通过的粉丝可以查看")

    # 查询该月签到记录
    from calendar import monthrange
    _, last_day = monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    checkins = db.query(FanCheckIn).filter(
        FanCheckIn.star_id == star_id,
        FanCheckIn.user_id == current_user.id,
        FanCheckIn.checkin_date >= start_date,
        FanCheckIn.checkin_date <= end_date
    ).all()

    checked_dates = [c.checkin_date.isoformat() for c in checkins]

    return FanCheckInCalendar(
        year=year,
        month=month,
        checked_dates=checked_dates
    )


@router.get("/{star_id}/checkin/rank", response_model=List[FanCheckInRankItem])
def get_checkin_rank(
    star_id: int,
    rank_type: str = Query("consecutive", pattern="^(consecutive|total)$", description="排行榜类型"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取签到排行榜"""
    star = db.query(Star).filter(Star.id == star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    if rank_type == "consecutive":
        # 按连续签到天数排行
        subquery = db.query(
            FanCheckIn.user_id,
            func.max(FanCheckIn.consecutive_days).label("max_consecutive"),
            func.count(FanCheckIn.id).label("total_days")
        ).filter(
            FanCheckIn.star_id == star_id
        ).group_by(FanCheckIn.user_id).subquery()

        results = db.query(subquery).order_by(
            subquery.c.max_consecutive.desc()
        ).limit(limit).all()

        rank_list = []
        for i, r in enumerate(results):
            user = db.query(User).filter(User.id == r.user_id).first()
            if user:
                rank_list.append(FanCheckInRankItem(
                    rank=i + 1,
                    user=UserPublic.model_validate(user),
                    total_days=r.total_days,
                    consecutive_days=r.max_consecutive
                ))
        return rank_list
    else:
        # 按累计签到天数排行
        subquery = db.query(
            FanCheckIn.user_id,
            func.count(FanCheckIn.id).label("total_days"),
            func.max(FanCheckIn.consecutive_days).label("max_consecutive")
        ).filter(
            FanCheckIn.star_id == star_id
        ).group_by(FanCheckIn.user_id).subquery()

        results = db.query(subquery).order_by(
            subquery.c.total_days.desc()
        ).limit(limit).all()

        rank_list = []
        for i, r in enumerate(results):
            user = db.query(User).filter(User.id == r.user_id).first()
            if user:
                rank_list.append(FanCheckInRankItem(
                    rank=i + 1,
                    user=UserPublic.model_validate(user),
                    total_days=r.total_days,
                    consecutive_days=r.max_consecutive
                ))
        return rank_list


@router.get("/{star_id}/checkin/history", response_model=List[FanCheckInPublic])
def get_checkin_history(
    star_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取我的签到历史"""
    star = db.query(Star).filter(Star.id == star_id, Star.is_active == True).first()
    if not star:
        raise HTTPException(status_code=404, detail="明星不存在")

    is_fan = db.query(StarFan).filter(
        StarFan.star_id == star_id,
        StarFan.user_id == current_user.id,
        StarFan.status == "approved"
    ).first()
    if not is_fan:
        raise HTTPException(status_code=403, detail="仅已通过的粉丝可以查看")

    checkins = db.query(FanCheckIn).filter(
        FanCheckIn.star_id == star_id,
        FanCheckIn.user_id == current_user.id
    ).order_by(FanCheckIn.checkin_date.desc())\
     .offset((page - 1) * page_size)\
     .limit(page_size).all()

    return [FanCheckInPublic.model_validate(c) for c in checkins]
