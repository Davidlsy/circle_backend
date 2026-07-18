from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from typing import List

from app.database import get_db
from app.models import User, Conversation, Message, Location
from app.schemas import (
    ConversationCreate, ConversationPublic, ConversationListItem, ConversationList,
    MessageSend, MessagePublic, MessageWithSender, MessageList,
    MarkReadResponse, Msg, LocationPublic, UserPublic
)
from app.auth import get_current_active_user

router = APIRouter(prefix="/messages", tags=["私信"])


def _get_or_create_conversation(db: Session, user1_id: int, user2_id: int) -> Conversation:
    """获取或创建两人之间的会话（确保 user1_id < user2_id 以保证唯一性）"""
    if user1_id == user2_id:
        raise HTTPException(status_code=400, detail="不能给自己发私信")

    # 统一排序，避免同一对用户产生两条会话
    uid_a, uid_b = sorted([user1_id, user2_id])

    conv = db.query(Conversation).filter(
        Conversation.user1_id == uid_a,
        Conversation.user2_id == uid_b
    ).first()

    if not conv:
        conv = Conversation(user1_id=uid_a, user2_id=uid_b)
        db.add(conv)
        db.commit()
        db.refresh(conv)

    return conv


def _other_user_in_conversation(conv: Conversation, current_user_id: int) -> User:
    """从会话中获取对方用户"""
    if conv.user1_id == current_user_id:
        return conv.user2
    return conv.user1


# ─── 会话管理 ───

@router.post("/conversations", response_model=ConversationPublic)
def get_or_create_conversation(
    data: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取或创建一个与目标用户的私信会话
    如果已有会话则返回已有会话，不重复创建
    """
    target = db.query(User).filter(User.id == data.target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    conv = _get_or_create_conversation(db, current_user.id, target.id)
    return conv


@router.get("/conversations", response_model=ConversationList)
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前用户的会话列表
    按最新消息时间倒序，含未读计数
    """
    convs = db.query(Conversation).filter(
        or_(
            Conversation.user1_id == current_user.id,
            Conversation.user2_id == current_user.id
        )
    ).order_by(Conversation.updated_at.desc()).all()

    result = []
    for conv in convs:
        other = _other_user_in_conversation(conv, current_user.id)

        # 最后一条消息
        last_msg = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).order_by(Message.created_at.desc()).first()

        # 未读数（对方发的且未读）
        unread = db.query(func.count(Message.id)).filter(
            Message.conversation_id == conv.id,
            Message.sender_id != current_user.id,
            Message.is_read == False
        ).scalar()

        result.append(ConversationListItem(
            id=conv.id,
            other_user=UserPublic.model_validate(other),
            last_message=MessagePublic.model_validate(last_msg) if last_msg else None,
            unread_count=unread,
            updated_at=conv.updated_at,
            created_at=conv.created_at
        ))

    return ConversationList(conversations=result, total=len(result))


# ─── 消息操作 ───

@router.post("/conversations/{conv_id}/messages", response_model=MessageWithSender)
def send_message(
    conv_id: int,
    data: MessageSend,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """在指定会话中发送消息（支持 text/image/sticker/location）"""
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 验证当前用户在会话中
    if current_user.id not in (conv.user1_id, conv.user2_id):
        raise HTTPException(status_code=403, detail="无权访问此会话")

    # 处理位置消息
    location_id = None
    if data.message_type == "location" and data.location:
        location = Location(
            latitude=data.location.latitude,
            longitude=data.location.longitude,
            name=data.location.name,
            address=data.location.address,
            poi_id=data.location.poi_id
        )
        db.add(location)
        db.flush()
        location_id = location.id

    msg = Message(
        conversation_id=conv_id,
        sender_id=current_user.id,
        content=data.content,
        message_type=data.message_type or "text",
        location_id=location_id
    )
    db.add(msg)

    # 更新会话最新时间
    conv.updated_at = msg.created_at
    db.commit()
    db.refresh(msg)

    result = MessageWithSender(
        id=msg.id,
        conversation_id=msg.conversation_id,
        sender_id=msg.sender_id,
        content=msg.content,
        message_type=msg.message_type,
        is_read=msg.is_read,
        created_at=msg.created_at,
        sender=UserPublic.model_validate(current_user)
    )

    # 添加位置信息
    if msg.location:
        result.location = LocationPublic.model_validate(msg.location)

    return result


@router.get("/conversations/{conv_id}/messages", response_model=MessageList)
def list_messages(
    conv_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取会话中的消息列表（分页，最新消息在前）"""
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    if current_user.id not in (conv.user1_id, conv.user2_id):
        raise HTTPException(status_code=403, detail="无权访问此会话")

    query = db.query(Message).filter(Message.conversation_id == conv_id)
    total = query.count()

    messages = query.order_by(Message.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()

    # 补充发送者信息（倒序展示，最新在上）
    result = []
    for m in reversed(messages):
        result.append(MessageWithSender(
            id=m.id,
            conversation_id=m.conversation_id,
            sender_id=m.sender_id,
            content=m.content,
            is_read=m.is_read,
            created_at=m.created_at,
            sender=UserPublic.model_validate(m.sender)
        ))

    return MessageList(messages=result, total=total, page=page, page_size=page_size)


@router.put("/conversations/{conv_id}/read", response_model=MarkReadResponse)
def mark_all_as_read(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    将会话中所有对方发的消息标记为已读
    """
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    if current_user.id not in (conv.user1_id, conv.user2_id):
        raise HTTPException(status_code=403, detail="无权访问此会话")

    read_count = db.query(Message).filter(
        Message.conversation_id == conv_id,
        Message.sender_id != current_user.id,
        Message.is_read == False
    ).update({"is_read": True})

    db.commit()
    return MarkReadResponse(msg="已标记为已读", read_count=read_count)


@router.get("/conversations/unread-count", response_model=dict)
def total_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取当前用户所有会话的未读消息总数"""
    total = db.query(func.count(Message.id)).filter(
        Message.sender_id != current_user.id,
        Message.is_read == False,
        or_(
            Message.conversation_id.in_(
                db.query(Conversation.id).filter(Conversation.user1_id == current_user.id)
            ),
            Message.conversation_id.in_(
                db.query(Conversation.id).filter(Conversation.user2_id == current_user.id)
            )
        )
    ).scalar()

    return {"unread_total": total}
