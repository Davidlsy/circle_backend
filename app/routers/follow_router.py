from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.database import get_db
from app.models import User, Follow
from app.schemas import (
    FollowResponse, FollowStatus, UserWithCounts,
    UserList, UserPublic, UserProfile, UserUpdate, Msg
)
from app.auth import get_current_active_user
from datetime import datetime

router = APIRouter(prefix="/users", tags=["关注"])


def _get_counts(db: Session, user_id: int) -> tuple[int, int]:
    """返回 (follower_count, following_count)"""
    follower_count = db.query(func.count(Follow.id)).filter(
        Follow.following_id == user_id
    ).scalar()
    following_count = db.query(func.count(Follow.id)).filter(
        Follow.follower_id == user_id
    ).scalar()
    return follower_count, following_count


def _is_following(db: Session, follower_id: int, following_id: int) -> bool:
    return db.query(Follow).filter(
        Follow.follower_id == follower_id,
        Follow.following_id == following_id
    ).first() is not None


# ─── 当前用户资料 ───

@router.patch("/me", response_model=UserProfile)
def update_my_profile(
    update_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    编辑当前用户的个人资料
    - nickname / avatar_url / bio / email / phone 均为选填
    - email/phone 如填写须唯一（不能和他人重复）
    """
    # 检查 email 唯一性
    if update_data.email:
        existing = db.query(User).filter(
            User.email == update_data.email,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="该邮箱已被使用")

    # 检查 phone 唯一性
    if update_data.phone:
        existing = db.query(User).filter(
            User.phone == update_data.phone,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="该手机号已被使用")

    # 更新有值的字段
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(current_user, key, value)

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)

    follower_count, following_count = _get_counts(db, current_user.id)
    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        nickname=current_user.nickname,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        created_at=current_user.created_at,
        follower_count=follower_count,
        following_count=following_count
    )


@router.get("/me", response_model=UserProfile)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取当前登录用户的个人资料（含粉丝数/关注数）"""
    follower_count, following_count = _get_counts(db, current_user.id)
    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        nickname=current_user.nickname,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        created_at=current_user.created_at,
        follower_count=follower_count,
        following_count=following_count
    )


@router.get("/{user_id}", response_model=UserProfile)
def get_user_profile(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    获取指定用户的公开资料（任何人可访问）
    - 返回基本信息及粉丝数/关注数
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    follower_count, following_count = _get_counts(db, user_id)
    return UserProfile(
        id=user.id,
        username=user.username,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        bio=user.bio,
        created_at=user.created_at,
        follower_count=follower_count,
        following_count=following_count
    )


# ─── 关注 / 取关 ───

@router.post("/{user_id}/follow", response_model=FollowResponse)
def toggle_follow(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """关注或取消关注指定用户"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能关注自己")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    existing = db.query(Follow).filter(
        Follow.follower_id == current_user.id,
        Follow.following_id == user_id
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        following = False
        msg = "取消关注成功"
    else:
        new_follow = Follow(follower_id=current_user.id, following_id=user_id)
        db.add(new_follow)
        db.commit()
        following = True
        msg = "关注成功"

    follower_count, following_count = _get_counts(db, current_user.id)
    return FollowResponse(
        msg=msg,
        following=following,
        follower_count=follower_count,
        following_count=following_count
    )


# ─── 关注状态（查看两人关系） ───

@router.get("/{user_id}/follow/status", response_model=FollowStatus)
def get_follow_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_active_user)
):
    """获取当前用户与目标用户的关注关系"""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    follower_count, following_count = _get_counts(db, user_id)

    is_following = False
    is_followed_by = False
    if current_user and current_user.id != user_id:
        is_following = _is_following(db, current_user.id, user_id)
        is_followed_by = _is_following(db, user_id, current_user.id)

    return FollowStatus(
        is_following=is_following,
        is_followed_by=is_followed_by,
        follower_count=follower_count,
        following_count=following_count
    )


# ─── 粉丝列表 ───

@router.get("/{user_id}/followers", response_model=UserList)
def list_followers(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """获取指定用户的粉丝列表"""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    query = db.query(Follow).filter(Follow.following_id == user_id)
    total = query.count()
    follows = query.order_by(Follow.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()

    users = []
    for f in follows:
        fc, fic = _get_counts(db, f.follower_id)
        users.append(UserWithCounts(
            id=f.follower.id,
            username=f.follower.username,
            nickname=f.follower.nickname,
            avatar_url=f.follower.avatar_url,
            bio=f.follower.bio,
            created_at=f.follower.created_at,
            follower_count=fc,
            following_count=fic
        ))

    return UserList(users=users, total=total)


# ─── 关注列表 ───

@router.get("/{user_id}/following", response_model=UserList)
def list_following(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """获取指定用户的关注列表"""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    query = db.query(Follow).filter(Follow.follower_id == user_id)
    total = query.count()
    follows = query.order_by(Follow.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()

    users = []
    for f in follows:
        fc, fic = _get_counts(db, f.following_id)
        users.append(UserWithCounts(
            id=f.following.id,
            username=f.following.username,
            nickname=f.following.nickname,
            avatar_url=f.following.avatar_url,
            bio=f.following.bio,
            created_at=f.following.created_at,
            follower_count=fc,
            following_count=fic
        ))

    return UserList(users=users, total=total)


# ─── 互相关注的好友列表 ───

@router.get("/me/friends", response_model=UserList)
def list_friends(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取当前用户互相关注的好友列表"""
    following_set = db.query(Follow.following_id).filter(
        Follow.follower_id == current_user.id
    ).all()
    following_ids_set = {f[0] for f in following_set}

    mutual_query = db.query(Follow).filter(
        Follow.follower_id == current_user.id,
        Follow.following_id.in_(following_ids_set),
        Follow.following_id.in_(
            db.query(Follow.follower_id).filter(Follow.following_id == current_user.id)
        )
    )

    total = mutual_query.count()
    follows = mutual_query.order_by(Follow.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()

    users = []
    for f in follows:
        fc, fic = _get_counts(db, f.following_id)
        users.append(UserWithCounts(
            id=f.following.id,
            username=f.following.username,
            nickname=f.following.nickname,
            avatar_url=f.following.avatar_url,
            bio=f.following.bio,
            created_at=f.following.created_at,
            follower_count=fc,
            following_count=fic
        ))

    return UserList(users=users, total=total)
