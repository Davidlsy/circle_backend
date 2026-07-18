"""
群聊模块路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from app.database import get_db
from app.models import User, GroupChat, GroupMember, GroupMessage, Location
from app.schemas import (
    GroupChatCreate, GroupChatUpdate, GroupChatPublic,
    GroupMemberPublic, GroupMessagePublic, GroupMessageCreate,
    GroupInviteRequest, GroupRoleUpdate, Msg, UserPublic, LocationPublic
)
from app.auth import get_current_active_user
from app.logging_config import logger

router = APIRouter(prefix="/groups", tags=["群聊"])


def _get_member_role(group_id: int, user_id: int, db: Session) -> Optional[str]:
    """获取用户在群中的角色，非成员返回 None"""
    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id
    ).first()
    return member.role if member else None


def _is_admin_or_owner(group_id: int, user_id: int, db: Session) -> bool:
    """检查用户是否是管理员或群主"""
    role = _get_member_role(group_id, user_id, db)
    return role in ("owner", "admin")


# ─── 群聊管理 ───

@router.post("/", response_model=GroupChatPublic, status_code=201)
def create_group(
    data: GroupChatCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """创建群聊（创建者自动成为群主）"""
    group = GroupChat(
        name=data.name,
        description=data.description,
        owner_id=current_user.id,
        max_members=data.max_members,
    )
    db.add(group)
    db.flush()

    # 创建者自动成为群主
    owner_member = GroupMember(
        group_id=group.id,
        user_id=current_user.id,
        role="owner",
    )
    db.add(owner_member)

    # 添加系统消息
    sys_msg = GroupMessage(
        group_id=group.id,
        sender_id=current_user.id,
        content=f"{current_user.username} 创建了群聊",
        message_type="system",
    )
    db.add(sys_msg)
    db.commit()
    db.refresh(group)

    # 返回成员数
    member_count = db.query(func.count(GroupMember.id)).filter(
        GroupMember.group_id == group.id
    ).scalar()
    result = GroupChatPublic.model_validate(group)
    result.member_count = member_count
    return result


@router.get("/", response_model=List[GroupChatPublic])
def list_my_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取我加入的群聊列表"""
    # 查询我所在的群
    my_group_ids = db.query(GroupMember.group_id).filter(
        GroupMember.user_id == current_user.id
    ).all()
    group_ids = [g[0] for g in my_group_ids]

    if not group_ids:
        return []

    groups = db.query(GroupChat).filter(
        GroupChat.id.in_(group_ids)
    ).order_by(GroupChat.updated_at.desc()).all()

    result = []
    for g in groups:
        item = GroupChatPublic.model_validate(g)
        item.member_count = db.query(func.count(GroupMember.id)).filter(
            GroupMember.group_id == g.id
        ).scalar()
        result.append(item)
    return result


@router.get("/{group_id}", response_model=GroupChatPublic)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取群聊详情"""
    group = db.query(GroupChat).filter(GroupChat.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群聊不存在")

    # 检查是否是成员
    role = _get_member_role(group_id, current_user.id, db)
    if not role:
        raise HTTPException(status_code=403, detail="您不是该群成员")

    result = GroupChatPublic.model_validate(group)
    result.member_count = db.query(func.count(GroupMember.id)).filter(
        GroupMember.group_id == group_id
    ).scalar()
    return result


@router.put("/{group_id}", response_model=GroupChatPublic)
def update_group(
    group_id: int,
    data: GroupChatUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """更新群聊信息（仅群主/管理员）"""
    group = db.query(GroupChat).filter(GroupChat.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群聊不存在")

    if not _is_admin_or_owner(group_id, current_user.id, db):
        raise HTTPException(status_code=403, detail="仅群主或管理员可修改群信息")

    if data.name is not None:
        group.name = data.name
    if data.description is not None:
        group.description = data.description
    if data.max_members is not None:
        group.max_members = data.max_members

    db.commit()
    db.refresh(group)

    result = GroupChatPublic.model_validate(group)
    result.member_count = db.query(func.count(GroupMember.id)).filter(
        GroupMember.group_id == group_id
    ).scalar()
    return result


@router.delete("/{group_id}", response_model=Msg)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """解散群聊（仅群主）"""
    group = db.query(GroupChat).filter(GroupChat.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群聊不存在")

    if group.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="仅群主可解散群聊")

    db.delete(group)
    db.commit()
    return Msg(msg="群聊已解散")


# ─── 成员管理 ───

@router.get("/{group_id}/members", response_model=List[GroupMemberPublic])
def list_members(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取群成员列表"""
    group = db.query(GroupChat).filter(GroupChat.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群聊不存在")

    role = _get_member_role(group_id, current_user.id, db)
    if not role:
        raise HTTPException(status_code=403, detail="您不是该群成员")

    members = db.query(GroupMember).filter(
        GroupMember.group_id == group_id
    ).order_by(GroupMember.joined_at).all()

    result = []
    for m in members:
        item = GroupMemberPublic.model_validate(m)
        user = db.query(User).filter(User.id == m.user_id).first()
        if user:
            item.user = UserPublic.model_validate(user)
        result.append(item)
    return result


@router.post("/{group_id}/invite", response_model=Msg)
def invite_members(
    group_id: int,
    data: GroupInviteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """邀请用户加入群聊（仅群主/管理员）"""
    group = db.query(GroupChat).filter(GroupChat.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群聊不存在")

    if not _is_admin_or_owner(group_id, current_user.id, db):
        raise HTTPException(status_code=403, detail="仅群主或管理员可邀请成员")

    # 检查当前成员数
    current_count = db.query(func.count(GroupMember.id)).filter(
        GroupMember.group_id == group_id
    ).scalar()

    if current_count + len(data.user_ids) > group.max_members:
        raise HTTPException(status_code=400, detail=f"群成员数不能超过 {group.max_members} 人")

    invited = 0
    for uid in data.user_ids:
        # 检查用户是否存在
        user = db.query(User).filter(User.id == uid).first()
        if not user:
            continue

        # 检查是否已是成员
        existing = db.query(GroupMember).filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == uid
        ).first()
        if existing:
            continue

        member = GroupMember(group_id=group_id, user_id=uid, role="member")
        db.add(member)
        invited += 1

    db.commit()

    if invited > 0:
        sys_msg = GroupMessage(
            group_id=group_id,
            sender_id=current_user.id,
            content=f"{current_user.username} 邀请了 {invited} 位成员加入群聊",
            message_type="system",
        )
        db.add(sys_msg)
        db.commit()

    return Msg(msg=f"成功邀请 {invited} 位成员")


@router.post("/{group_id}/join", response_model=Msg)
def join_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """加入群聊"""
    group = db.query(GroupChat).filter(GroupChat.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群聊不存在")

    existing = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="您已经是群成员")

    current_count = db.query(func.count(GroupMember.id)).filter(
        GroupMember.group_id == group_id
    ).scalar()
    if current_count >= group.max_members:
        raise HTTPException(status_code=400, detail="群成员已满")

    member = GroupMember(group_id=group_id, user_id=current_user.id, role="member")
    db.add(member)
    db.commit()

    sys_msg = GroupMessage(
        group_id=group_id,
        sender_id=current_user.id,
        content=f"{current_user.username} 加入了群聊",
        message_type="system",
    )
    db.add(sys_msg)
    db.commit()

    return Msg(msg="已加入群聊")


@router.post("/{group_id}/leave", response_model=Msg)
def leave_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """退出群聊"""
    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == current_user.id
    ).first()
    if not member:
        raise HTTPException(status_code=400, detail="您不是群成员")

    if member.role == "owner":
        raise HTTPException(status_code=400, detail="群主不能退出，请先转让群主或解散群聊")

    db.delete(member)
    db.commit()

    sys_msg = GroupMessage(
        group_id=group_id,
        sender_id=current_user.id,
        content=f"{current_user.username} 退出了群聊",
        message_type="system",
    )
    db.add(sys_msg)
    db.commit()

    return Msg(msg="已退出群聊")


@router.delete("/{group_id}/members/{user_id}", response_model=Msg)
def remove_member(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """移除群成员（仅群主/管理员）"""
    if not _is_admin_or_owner(group_id, current_user.id, db):
        raise HTTPException(status_code=403, detail="仅群主或管理员可移除成员")

    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="该用户不是群成员")

    if member.role == "owner":
        raise HTTPException(status_code=400, detail="不能移除群主")

    # 管理员不能移除其他管理员
    if member.role == "admin" and _get_member_role(group_id, current_user.id, db) != "owner":
        raise HTTPException(status_code=403, detail="仅群主可移除管理员")

    removed_user = db.query(User).filter(User.id == user_id).first()
    db.delete(member)
    db.commit()

    if removed_user:
        sys_msg = GroupMessage(
            group_id=group_id,
            sender_id=current_user.id,
            content=f"{current_user.username} 将 {removed_user.username} 移出群聊",
            message_type="system",
        )
        db.add(sys_msg)
        db.commit()

    return Msg(msg="成员已移除")


@router.patch("/{group_id}/members/{user_id}/role", response_model=Msg)
def update_member_role(
    group_id: int,
    user_id: int,
    data: GroupRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """设置成员角色（仅群主）"""
    group = db.query(GroupChat).filter(GroupChat.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群聊不存在")

    if group.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="仅群主可设置成员角色")

    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="该用户不是群成员")

    if member.role == "owner":
        raise HTTPException(status_code=400, detail="不能修改群主角色")

    member.role = data.role
    db.commit()

    return Msg(msg=f"已将成员角色设置为 {data.role}")


# ─── 群消息 ───

@router.get("/{group_id}/messages", response_model=List[GroupMessagePublic])
def list_messages(
    group_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取群聊消息列表"""
    role = _get_member_role(group_id, current_user.id, db)
    if not role:
        raise HTTPException(status_code=403, detail="您不是该群成员")

    messages = db.query(GroupMessage).filter(
        GroupMessage.group_id == group_id
    ).order_by(GroupMessage.created_at.desc())\
     .offset((page - 1) * page_size)\
     .limit(page_size).all()

    result = []
    for m in messages:
        item = GroupMessagePublic.model_validate(m)
        sender = db.query(User).filter(User.id == m.sender_id).first()
        if sender:
            item.sender = UserPublic.model_validate(sender)
        result.append(item)
    return result


@router.post("/{group_id}/messages", response_model=GroupMessagePublic)
def send_message(
    group_id: int,
    data: GroupMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """发送群消息（支持 text/image/sticker/location）"""
    role = _get_member_role(group_id, current_user.id, db)
    if not role:
        raise HTTPException(status_code=403, detail="您不是该群成员")

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

    msg = GroupMessage(
        group_id=group_id,
        sender_id=current_user.id,
        content=data.content,
        message_type=data.message_type,
        location_id=location_id
    )
    db.add(msg)

    # 更新群的 updated_at
    group = db.query(GroupChat).filter(GroupChat.id == group_id).first()
    if group:
        from datetime import datetime
        group.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(msg)

    result = GroupMessagePublic.model_validate(msg)
    result.sender = UserPublic.model_validate(current_user)

    # 添加位置信息
    if msg.location:
        result.location = LocationPublic.model_validate(msg.location)

    return result
