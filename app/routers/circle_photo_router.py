"""
粉丝圈共同空间照片模块路由

所有粉丝都可以上传照片，照片需要经过审核后才能公开显示
"""
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from app.database import get_db
from app.models import User, Star, StarFan, FanCircle, FanCirclePhoto
from app.schemas import (
    FanCirclePhotoPublic, FanCirclePhotoList, FanCirclePhotoAuditRequest,
    Msg, UserPublic
)
from app.auth import get_current_active_user
from app.logging_config import logger

router = APIRouter(prefix="/fan-circles", tags=["粉丝圈共同空间"])

# 图片上传目录
UPLOAD_DIR = "uploads/circle_photos"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _check_fan_permission(circle_id: int, user_id: int, db: Session) -> FanCircle:
    """检查用户是否是该粉丝圈的已通过粉丝"""
    circle = db.query(FanCircle).filter(FanCircle.id == circle_id).first()
    if not circle:
        raise HTTPException(status_code=404, detail="粉丝圈不存在")

    is_fan = db.query(StarFan).filter(
        StarFan.star_id == circle.star_id,
        StarFan.user_id == user_id,
        StarFan.status == "approved"
    ).first()

    if not is_fan:
        raise HTTPException(status_code=403, detail="仅该粉丝圈的粉丝可以操作")

    return circle


# ─── 照片上传与查看 ───

@router.post("/{circle_id}/photos", response_model=FanCirclePhotoPublic)
async def upload_photo(
    circle_id: int,
    file: UploadFile = File(..., description="图片文件"),
    description: Optional[str] = Form(None, max_length=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    上传照片到粉丝圈共同空间
    
    - 仅已通过的粉丝可上传
    - 支持 jpeg/png/gif/webp 格式
    - 单文件最大 5MB
    - 照片需要审核后才能公开显示
    """
    _check_fan_permission(circle_id, current_user.id, db)

    # 验证文件类型
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="仅支持 jpeg/png/gif/webp 格式")

    # 验证文件大小
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过 5MB")

    # 保存文件
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(content)

    # 创建记录
    photo = FanCirclePhoto(
        circle_id=circle_id,
        user_id=current_user.id,
        url=f"/uploads/circle_photos/{filename}",
        filename=file.filename,
        description=description,
        status="pending"
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)

    result = FanCirclePhotoPublic.model_validate(photo)
    result.user = UserPublic.model_validate(current_user)
    return result


@router.get("/{circle_id}/photos", response_model=FanCirclePhotoList)
def list_approved_photos(
    circle_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取粉丝圈已审核通过的照片列表（公开）"""
    circle = db.query(FanCircle).filter(FanCircle.id == circle_id).first()
    if not circle:
        raise HTTPException(status_code=404, detail="粉丝圈不存在")

    query = db.query(FanCirclePhoto).filter(
        FanCirclePhoto.circle_id == circle_id,
        FanCirclePhoto.status == "approved"
    )

    total = query.count()
    photos = query.order_by(FanCirclePhoto.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    result = []
    for p in photos:
        item = FanCirclePhotoPublic.model_validate(p)
        user = db.query(User).filter(User.id == p.user_id).first()
        if user:
            item.user = UserPublic.model_validate(user)
        result.append(item)

    return FanCirclePhotoList(photos=result, total=total, page=page, page_size=page_size)


@router.get("/{circle_id}/photos/all", response_model=FanCirclePhotoList)
def list_all_photos(
    circle_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取粉丝圈所有照片（含待审核，仅管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅管理员可查看所有照片")

    circle = db.query(FanCircle).filter(FanCircle.id == circle_id).first()
    if not circle:
        raise HTTPException(status_code=404, detail="粉丝圈不存在")

    query = db.query(FanCirclePhoto).filter(FanCirclePhoto.circle_id == circle_id)

    total = query.count()
    photos = query.order_by(FanCirclePhoto.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    result = []
    for p in photos:
        item = FanCirclePhotoPublic.model_validate(p)
        user = db.query(User).filter(User.id == p.user_id).first()
        if user:
            item.user = UserPublic.model_validate(user)
        result.append(item)

    return FanCirclePhotoList(photos=result, total=total, page=page, page_size=page_size)


@router.get("/{circle_id}/photos/my", response_model=FanCirclePhotoList)
def list_my_photos(
    circle_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取我在该粉丝圈上传的照片"""
    _check_fan_permission(circle_id, current_user.id, db)

    query = db.query(FanCirclePhoto).filter(
        FanCirclePhoto.circle_id == circle_id,
        FanCirclePhoto.user_id == current_user.id
    )

    total = query.count()
    photos = query.order_by(FanCirclePhoto.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    result = []
    for p in photos:
        item = FanCirclePhotoPublic.model_validate(p)
        item.user = UserPublic.model_validate(current_user)
        result.append(item)

    return FanCirclePhotoList(photos=result, total=total, page=page, page_size=page_size)


@router.get("/{circle_id}/photos/pending", response_model=FanCirclePhotoList)
def list_pending_photos(
    circle_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取待审核的照片列表（仅管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅管理员可查看待审核照片")

    circle = db.query(FanCircle).filter(FanCircle.id == circle_id).first()
    if not circle:
        raise HTTPException(status_code=404, detail="粉丝圈不存在")

    query = db.query(FanCirclePhoto).filter(
        FanCirclePhoto.circle_id == circle_id,
        FanCirclePhoto.status == "pending"
    )

    total = query.count()
    photos = query.order_by(FanCirclePhoto.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    result = []
    for p in photos:
        item = FanCirclePhotoPublic.model_validate(p)
        user = db.query(User).filter(User.id == p.user_id).first()
        if user:
            item.user = UserPublic.model_validate(user)
        result.append(item)

    return FanCirclePhotoList(photos=result, total=total, page=page, page_size=page_size)


# ─── 照片审核 ───

@router.post("/{circle_id}/photos/{photo_id}/audit", response_model=FanCirclePhotoPublic)
def audit_photo(
    circle_id: int,
    photo_id: int,
    data: FanCirclePhotoAuditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """审核照片（仅管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅管理员可审核照片")

    photo = db.query(FanCirclePhoto).filter(
        FanCirclePhoto.id == photo_id,
        FanCirclePhoto.circle_id == circle_id
    ).first()

    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")

    if photo.status != "pending":
        raise HTTPException(status_code=400, detail="该照片已审核")

    photo.status = data.status
    photo.reviewed_by = current_user.id
    photo.reviewed_at = datetime.utcnow()

    if data.status == "rejected":
        photo.reject_reason = data.reject_reason

    db.commit()
    db.refresh(photo)

    result = FanCirclePhotoPublic.model_validate(photo)
    user = db.query(User).filter(User.id == photo.user_id).first()
    if user:
        result.user = UserPublic.model_validate(user)
    return result


@router.post("/{circle_id}/photos/{photo_id}/approve", response_model=FanCirclePhotoPublic)
def approve_photo(
    circle_id: int,
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """快捷通过照片（仅管理员）"""
    return audit_photo(circle_id, photo_id, FanCirclePhotoAuditRequest(status="approved"), db, current_user)


@router.post("/{circle_id}/photos/{photo_id}/reject", response_model=FanCirclePhotoPublic)
def reject_photo(
    circle_id: int,
    photo_id: int,
    reject_reason: Optional[str] = Query(None, max_length=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """快捷驳回照片（仅管理员）"""
    return audit_photo(circle_id, photo_id, FanCirclePhotoAuditRequest(status="rejected", reject_reason=reject_reason), db, current_user)


# ─── 照片删除 ───

@router.delete("/{circle_id}/photos/{photo_id}", response_model=Msg)
def delete_photo(
    circle_id: int,
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除照片（仅上传者或管理员）"""
    photo = db.query(FanCirclePhoto).filter(
        FanCirclePhoto.id == photo_id,
        FanCirclePhoto.circle_id == circle_id
    ).first()

    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")

    if photo.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅上传者或管理员可删除")

    # 删除文件
    if photo.url:
        filename = photo.url.split("/")[-1]
        filepath = os.path.join(UPLOAD_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)

    db.delete(photo)
    db.commit()

    return Msg(msg="照片已删除")
