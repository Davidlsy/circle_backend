"""
举报模块路由
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from app.database import get_db
from app.models import User, Post, Report
from app.schemas import (
    ReportCreate, ReportHandleRequest, ReportPublic, ReportList,
    ReportReasonsResponse, REPORT_REASONS, Msg, UserPublic
)
from app.auth import get_current_active_user
from app.logging_config import logger

router = APIRouter(prefix="/reports", tags=["举报"])


# ─── 用户举报 ───

@router.get("/reasons", response_model=ReportReasonsResponse)
def get_report_reasons():
    """获取举报原因分类列表"""
    return ReportReasonsResponse(reasons=REPORT_REASONS)


@router.post("/", response_model=ReportPublic, status_code=201)
def create_report(
    data: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """举报帖子"""
    # 验证帖子存在
    post = db.query(Post).filter(Post.id == data.post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")

    # 验证举报原因
    if data.reason not in REPORT_REASONS:
        raise HTTPException(
            status_code=400,
            detail=f"举报原因无效，可选值：{', '.join(REPORT_REASONS)}"
        )

    # 检查是否重复举报（同一用户对同一帖子只能举报一次待处理的）
    existing = db.query(Report).filter(
        Report.reporter_id == current_user.id,
        Report.post_id == data.post_id,
        Report.status.in_(["pending", "processing"])
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="您已举报过该帖子，请等待处理")

    report = Report(
        reporter_id=current_user.id,
        post_id=data.post_id,
        reason=data.reason,
        description=data.description,
        status="pending"
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    result = ReportPublic.model_validate(report)
    result.reporter = UserPublic.model_validate(current_user)
    return result


@router.get("/my", response_model=ReportList)
def list_my_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取我的举报记录"""
    query = db.query(Report).filter(Report.reporter_id == current_user.id)

    total = query.count()
    reports = query.order_by(Report.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    result = []
    for r in reports:
        item = ReportPublic.model_validate(r)
        item.reporter = UserPublic.model_validate(current_user)
        handler = db.query(User).filter(User.id == r.handled_by).first()
        if handler:
            item.handler = UserPublic.model_validate(handler)
        result.append(item)

    return ReportList(reports=result, total=total, page=page, page_size=page_size)


# ─── 管理员处理举报 ───

@router.get("/", response_model=ReportList)
def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, pattern="^(pending|processing|resolved|dismissed)$"),
    post_id: Optional[int] = Query(None, description="按帖子筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取举报列表（管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅管理员可查看举报列表")

    query = db.query(Report)

    if status:
        query = query.filter(Report.status == status)
    if post_id:
        query = query.filter(Report.post_id == post_id)

    total = query.count()
    reports = query.order_by(Report.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size).all()

    result = []
    for r in reports:
        item = ReportPublic.model_validate(r)
        reporter = db.query(User).filter(User.id == r.reporter_id).first()
        if reporter:
            item.reporter = UserPublic.model_validate(reporter)
        handler = db.query(User).filter(User.id == r.handled_by).first()
        if handler:
            item.handler = UserPublic.model_validate(handler)
        result.append(item)

    return ReportList(reports=result, total=total, page=page, page_size=page_size)


@router.get("/stats", response_model=dict)
def get_report_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取举报统计数据（管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅管理员可查看统计数据")

    stats = db.query(
        Report.status,
        func.count(Report.id).label("count")
    ).group_by(Report.status).all()

    result = {s.status: s.count for s in stats}
    result["total"] = sum(result.values())
    return result


@router.get("/{report_id}", response_model=ReportPublic)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取举报详情"""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="举报记录不存在")

    # 仅举报人或管理员可查看
    if report.reporter_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="无权查看此举报")

    result = ReportPublic.model_validate(report)
    reporter = db.query(User).filter(User.id == report.reporter_id).first()
    if reporter:
        result.reporter = UserPublic.model_validate(reporter)
    handler = db.query(User).filter(User.id == report.handled_by).first()
    if handler:
        result.handler = UserPublic.model_validate(handler)
    return result


@router.post("/{report_id}/handle", response_model=ReportPublic)
def handle_report(
    report_id: int,
    data: ReportHandleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """处理举报（管理员）"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="仅管理员可处理举报")

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="举报记录不存在")

    if report.status not in ("pending", "processing"):
        raise HTTPException(status_code=400, detail="该举报已处理")

    report.status = data.status
    report.handled_by = current_user.id
    report.handle_result = data.handle_result
    report.handled_at = datetime.utcnow()

    # 如果举报成立，自动驳回帖子
    if data.status == "resolved":
        post = db.query(Post).filter(Post.id == report.post_id).first()
        if post and post.status == "approved":
            post.status = "rejected"
            logger.info(f"帖子 {post.id} 因举报成立被自动驳回")

    db.commit()
    db.refresh(report)

    result = ReportPublic.model_validate(report)
    reporter = db.query(User).filter(User.id == report.reporter_id).first()
    if reporter:
        result.reporter = UserPublic.model_validate(reporter)
    result.handler = UserPublic.model_validate(current_user)
    return result
