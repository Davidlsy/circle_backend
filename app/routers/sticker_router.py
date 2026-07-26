"""
表情包模块路由

用户可以上传表情包、收藏表情包、在聊天中使用表情包
"""
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from app.database import get_db
from app.models import User, Sticker, UserSticker
from app.schemas import (
    StickerPublic, StickerList, UserStickerPublic, UserStickerList,
    MAX_USER_STICKERS, Msg
)
from app.auth import get_current_active_user
from app.logging_config import logger

router = APIRouter(prefix="/stickers", tags=["表情包"])

# 表情包上传目录
UPLOAD_DIR = "uploads/stickers"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─── 表情包管理（管理员上传公开表情包） ───

@router.post("/", response_model=StickerPublic)
async def upload_sticker(
    file: UploadFile = File(..., description="表情包图片"),
    name: str = Form(..., min_length=1, max_length=100, description="表情包名称"),
    category: Optional[str] = Form("default", description="分类：default/emoji/custom"),
    is_public: bool = Form(True, description="是否公开"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    上传表情包
    
    - 支持格式：gif/webp/png
    - 单文件最大 2MB
    - 公开表情包所有用户可见
    """
    allowed_types = ["image/gif", "image/webp", "image/png"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="仅支持 gif/webp/png 格式")

    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过 2MB")

    ext = file.filename.split(".")[-1] if "." in file.filename else "gif"
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(content)

    sticker = Sticker(
        name=name,
        url=f"/uploads/stickers/{filename}",
        filename=file.filename,
        category=category,
        is_public=is_public,
        uploader_id=current_user.id
    )
    db.add(sticker)
    db.commit()
    db.refresh(sticker)

    return StickerPublic.model_validate(sticker)


@router.get("/", response_model=StickerList)
def list_stickers(
    category: Optional[str] = Query(None, description="按分类筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """获取公开表情包列表（所有用户可用）"""
    query = db.query(Sticker).filter(Sticker.is_public == True)

    if category:
        query = query.filter(Sticker.category == category)

    total = query.count()
    stickers = query.order_by(Sticker.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    return StickerList(
        stickers=[StickerPublic.model_validate(s) for s in stickers],
        total=total
    )


@router.get("/search", response_model=StickerList)
def search_stickers(
    keyword: str = Query(..., min_length=1, max_length=50),
    db: Session = Depends(get_db)
):
    """搜索表情包"""
    stickers = db.query(Sticker).filter(
        Sticker.is_public == True,
        Sticker.name.contains(keyword)
    ).order_by(Sticker.created_at.desc()).limit(20).all()

    return StickerList(
        stickers=[StickerPublic.model_validate(s) for s in stickers],
        total=len(stickers)
    )


@router.get("/categories", response_model=dict)
def get_sticker_categories(db: Session = Depends(get_db)):
    """获取表情包分类列表"""
    categories = db.query(
        Sticker.category,
        func.count(Sticker.id).label("count")
    ).filter(
        Sticker.is_public == True
    ).group_by(Sticker.category).all()

    return {"categories": [{"name": c.category, "count": c.count} for c in categories]}


@router.delete("/{sticker_id}", response_model=Msg)
def delete_sticker(
    sticker_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """删除表情包（仅上传者或管理员）"""
    sticker = db.query(Sticker).filter(Sticker.id == sticker_id).first()
    if not sticker:
        raise HTTPException(status_code=404, detail="表情包不存在")

    if sticker.uploader_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅上传者或管理员可删除")

    # 删除文件
    if sticker.url:
        fname = sticker.url.split("/")[-1]
        filepath = os.path.join(UPLOAD_DIR, fname)
        if os.path.exists(filepath):
            os.remove(filepath)

    # 删除用户收藏
    db.query(UserSticker).filter(UserSticker.sticker_id == sticker_id).delete()

    db.delete(sticker)
    db.commit()

    return Msg(msg="表情包已删除")


# ─── 用户表情包收藏 ───

@router.get("/my", response_model=UserStickerList)
def list_my_stickers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取我的表情包收藏列表"""
    query = db.query(UserSticker).filter(UserSticker.user_id == current_user.id)

    total = query.count()
    stickers = query.order_by(UserSticker.sort_order, UserSticker.created_at).all()

    result = []
    for us in stickers:
        item = UserStickerPublic.model_validate(us)
        sticker = db.query(Sticker).filter(Sticker.id == us.sticker_id).first()
        if sticker:
            item.sticker = StickerPublic.model_validate(sticker)
        result.append(item)

    return UserStickerList(stickers=result, total=total)


@router.post("/my/{sticker_id}", response_model=Msg)
def add_sticker_to_my_collection(
    sticker_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """收藏表情包到我的收藏（上限 100 个）"""
    # 检查表情包是否存在
    sticker = db.query(Sticker).filter(Sticker.id == sticker_id).first()
    if not sticker:
        raise HTTPException(status_code=404, detail="表情包不存在")

    # 检查是否已收藏
    existing = db.query(UserSticker).filter(
        UserSticker.user_id == current_user.id,
        UserSticker.sticker_id == sticker_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="已收藏该表情包")

    # 检查收藏上限
    count = db.query(func.count(UserSticker.id)).filter(
        UserSticker.user_id == current_user.id
    ).scalar() or 0

    if count >= MAX_USER_STICKERS:
        raise HTTPException(
            status_code=400,
            detail=f"表情包收藏已达上限（{MAX_USER_STICKERS}个），请先移除不需要的"
        )

    # 获取最大排序值
    max_order = db.query(func.max(UserSticker.sort_order)).filter(
        UserSticker.user_id == current_user.id
    ).scalar() or 0

    user_sticker = UserSticker(
        user_id=current_user.id,
        sticker_id=sticker_id,
        sort_order=max_order + 1
    )
    db.add(user_sticker)
    db.commit()

    return Msg(msg="已收藏表情包")


@router.delete("/my/{sticker_id}", response_model=Msg)
def remove_sticker_from_my_collection(
    sticker_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """从我的收藏中移除表情包"""
    user_sticker = db.query(UserSticker).filter(
        UserSticker.user_id == current_user.id,
        UserSticker.sticker_id == sticker_id
    ).first()

    if not user_sticker:
        raise HTTPException(status_code=404, detail="未收藏该表情包")

    db.delete(user_sticker)
    db.commit()

    return Msg(msg="已移除表情包")


@router.get("/my/count", response_model=dict)
def get_my_sticker_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取我的表情包收藏数量"""
    count = db.query(func.count(UserSticker.id)).filter(
        UserSticker.user_id == current_user.id
    ).scalar() or 0

    return {"count": count, "max": MAX_USER_STICKERS}
