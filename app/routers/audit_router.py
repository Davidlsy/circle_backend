from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Literal

from app.database import get_db
from app.models import User, Post, Comment
from app.schemas import (
    AuditRequest, AuditResponse,
    PendingPostItem, PendingPostList,
    PendingCommentItem, PendingCommentList,
    Msg, UserPublic
)
from app.auth import get_current_active_user

router = APIRouter(prefix="/admin", tags=["内容审核"])


def _is_admin(user: User) -> bool:
    return user.is_superuser


def _require_admin(current_user: User = Depends(get_current_active_user)):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


# ─── 帖子审核 ───

@router.get("/posts/pending", response_model=PendingPostList)
def list_pending_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin)
):
    """
    获取待审核帖子列表（仅管理员）
    """
    query = db.query(Post).filter(Post.status == "pending")
    total = query.count()
    posts = query.order_by(Post.created_at.asc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()

    return PendingPostList(
        posts=[PendingPostItem(
            id=p.id,
            title=p.title,
            content=p.content,
            author=UserPublic.model_validate(p.author),
            created_at=p.created_at
        ) for p in posts],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/posts/rejected", response_model=PendingPostList)
def list_rejected_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin)
):
    """获取已驳回帖子列表"""
    query = db.query(Post).filter(Post.status == "rejected")
    total = query.count()
    posts = query.order_by(Post.updated_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()

    return PendingPostList(
        posts=[PendingPostItem(
            id=p.id,
            title=p.title,
            content=p.content,
            author=UserPublic.model_validate(p.author),
            created_at=p.created_at
        ) for p in posts],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/posts/{post_id}/audit", response_model=AuditResponse)
def audit_post(
    post_id: int,
    data: AuditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin)
):
    """
    审核帖子（仅管理员）
    status: approved 或 rejected
    """
    if data.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="status 只能为 approved 或 rejected")

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    post.status = data.status
    db.commit()
    db.refresh(post)

    return AuditResponse(
        msg=f"帖子已{data.status}",
        id=post.id,
        status=post.status
    )


@router.post("/posts/{post_id}/approve", response_model=AuditResponse)
def approve_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin)
):
    """快捷通过帖子"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    post.status = "approved"
    db.commit()
    return AuditResponse(msg="帖子已通过", id=post.id, status="approved")


@router.post("/posts/{post_id}/reject", response_model=AuditResponse)
def reject_post(
    post_id: int,
    reason: str = Query(None, max_length=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin)
):
    """快捷驳回帖子"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    post.status = "rejected"
    db.commit()
    return AuditResponse(msg="帖子已驳回", id=post.id, status="rejected")


# ─── 评论审核 ───

@router.get("/comments/pending", response_model=PendingCommentList)
def list_pending_comments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin)
):
    """获取待审核评论列表"""
    query = db.query(Comment).filter(Comment.status == "pending")
    total = query.count()
    comments = query.order_by(Comment.created_at.asc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()

    return PendingCommentList(
        comments=[PendingCommentItem(
            id=c.id,
            content=c.content,
            author=UserPublic.model_validate(c.author),
            post_id=c.post_id,
            created_at=c.created_at
        ) for c in comments],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/comments/{comment_id}/audit", response_model=AuditResponse)
def audit_comment(
    comment_id: int,
    data: AuditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin)
):
    """审核评论"""
    if data.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="status 只能为 approved 或 rejected")

    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")

    comment.status = data.status
    db.commit()
    db.refresh(comment)
    return AuditResponse(msg=f"评论已{data.status}", id=comment.id, status=comment.status)


@router.post("/comments/{comment_id}/approve", response_model=AuditResponse)
def approve_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin)
):
    """快捷通过评论"""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    comment.status = "approved"
    db.commit()
    return AuditResponse(msg="评论已通过", id=comment.id, status="approved")


@router.post("/comments/{comment_id}/reject", response_model=AuditResponse)
def reject_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin)
):
    """快捷驳回评论"""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    comment.status = "rejected"
    db.commit()
    return AuditResponse(msg="评论已驳回", id=comment.id, status="rejected")
