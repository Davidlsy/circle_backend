"""
公共工具函数

提取重复使用的业务逻辑为公共函数，减少代码重复
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.models import User, StarFan, Star
from app.schemas import UserPublic


def check_fan_permission(
    star_id: int,
    user_id: int,
    db: Session,
    error_msg: str = "仅该明星的已通过粉丝可执行此操作"
) -> Optional[StarFan]:
    """
    检查用户是否是某明星的已通过粉丝
    
    Args:
        star_id: 明星ID
        user_id: 用户ID
        db: 数据库会话
        error_msg: 权限不足时的错误消息
    
    Returns:
        StarFan 对象（如果验证通过）
    
    Raises:
        HTTPException: 403 如果不是已通过粉丝
    """
    fan = db.query(StarFan).filter(
        StarFan.star_id == star_id,
        StarFan.user_id == user_id,
        StarFan.status == "approved"
    ).first()

    if not fan:
        raise HTTPException(status_code=403, detail=error_msg)

    return fan


def get_user_public_with_badge(user_id: int, db: Session) -> dict:
    """
    获取用户公开资料（含展示的粉丝牌）
    
    Args:
        user_id: 用户ID
        db: 数据库会话
    
    Returns:
        用户公开资料字典
    """
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    result = {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "political_status": user.political_status,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }

    # 获取展示的粉丝牌
    from app.models import FanBadge
    from app.schemas import FanBadgePublic, StarPublic

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

    return result
