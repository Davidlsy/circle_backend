from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Index, UniqueConstraint, Float, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    phone = Column(String(20), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    nickname = Column(String(50), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(String(200), nullable=True)
    political_status = Column(String(20), default="masses", nullable=True)  # 政治面貌：masses(群众)/league(共青团员)/party(中共党员)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")

    # 关注：主动关注（我关注的人）
    following = relationship(
        "Follow",
        foreign_keys="Follow.follower_id",
        back_populates="follower",
        cascade="all, delete-orphan"
    )
    # 关注：被动被关注（我的粉丝）
    followers = relationship(
        "Follow",
        foreign_keys="Follow.following_id",
        back_populates="following",
        cascade="all, delete-orphan"
    )

    # 收藏
    collections = relationship(
        "Collection",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # 私信：发起的会话（作为 user1 或 user2）
    conversations_as_user1 = relationship(
        "Conversation",
        foreign_keys="Conversation.user1_id",
        back_populates="user1",
        cascade="all, delete-orphan"
    )
    conversations_as_user2 = relationship(
        "Conversation",
        foreign_keys="Conversation.user2_id",
        back_populates="user2",
        cascade="all, delete-orphan"
    )
    # 发出的消息
    sent_messages = relationship(
        "Message",
        foreign_keys="Message.sender_id",
        back_populates="sender",
        cascade="all, delete-orphan"
    )
    # 关注的明星
    following_stars = relationship(
        "StarFollow",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    # 粉丝申请
    fan_applications = relationship(
        "StarFan",
        foreign_keys="StarFan.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    # 风纪委员会申请
    committee_applications = relationship(
        "DisciplineCommittee",
        foreign_keys="DisciplineCommittee.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    # 签到记录
    checkins = relationship(
        "FanCheckIn",
        foreign_keys="FanCheckIn.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    # 第三方账号绑定（v2 新增）
    oauth_accounts = relationship(
        "OauthAccount",
        foreign_keys="OauthAccount.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    # 粉丝牌记录
    fan_badges = relationship(
        "FanBadge",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    # 粉丝圈照片
    circle_photos = relationship(
        "FanCirclePhoto",
        foreign_keys="FanCirclePhoto.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    # 用户表情包收藏
    user_stickers = relationship(
        "UserSticker",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    # 举报记录
    reports_made = relationship(
        "Report",
        foreign_keys="Report.reporter_id",
        back_populates="reporter",
        cascade="all, delete-orphan"
    )


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    content = Column(Text, nullable=False)
    content_format = Column(String(20), default="markdown", nullable=False)  # markdown / html / plain
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_published = Column(Boolean, default=True)
    view_count = Column(Integer, default=0)
    is_pinned = Column(Boolean, default=False)    # 是否置顶
    is_featured = Column(Boolean, default=False)   # 是否加精
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")
    images = relationship("PostImage", back_populates="post", cascade="all, delete-orphan")
    videos = relationship("PostVideo", back_populates="post", cascade="all, delete-orphan")
    collections = relationship("Collection", back_populates="post", cascade="all, delete-orphan")
    tags = relationship("PostTag", back_populates="post", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="post", cascade="all, delete-orphan")

    # 内容审核状态: pending(待审) / approved(通过) / rejected(驳回)
    status = Column(String(20), default="pending", nullable=False)


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=True)  # 回复功能
    status = Column(String(20), default="pending", nullable=False)  # pending / approved / rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    author = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")
    replies = relationship("Comment", back_populates="parent", cascade="all, delete-orphan")
    parent = relationship("Comment", back_populates="replies", remote_side=[id])
    likes = relationship("CommentLike", back_populates="comment", cascade="all, delete-orphan")


class Like(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    user = relationship("User")
    post = relationship("Post", back_populates="likes")


class CommentLike(Base):
    """评论点赞表"""
    __tablename__ = "comment_likes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    comment_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    user = relationship("User")
    comment = relationship("Comment", back_populates="likes")

    __table_args__ = (
        # 点赞去重：同一用户对同一评论只能点赞一次
        UniqueConstraint("user_id", "comment_id", name="uq_comment_like_user_comment"),
        # 按评论查点赞用户
        Index("ix_commentlike_comment_user", "comment_id", "user_id"),
        # 按用户查点赞评论
        Index("ix_commentlike_user_comment", "user_id", "comment_id"),
    )


class Collection(Base):
    """收藏表"""
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="collections")
    post = relationship("Post", back_populates="collections")


class Follow(Base):
    """关注关系表"""
    __tablename__ = "follows"

    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)   # 谁关注
    following_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False) # 关注谁
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    follower = relationship("User", foreign_keys=[follower_id], back_populates="following")
    following = relationship("User", foreign_keys=[following_id], back_populates="followers")


class VerificationCode(Base):
    """验证码表（用于找回密码等场景）"""
    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    code = Column(String(255), nullable=False)     # 验证码（存储时加密，长度支持哈希值）
    purpose = Column(String(20), default="reset_password")  # 用途：reset_password / change_phone 等
    expires_at = Column(DateTime, nullable=False)  # 过期时间
    used = Column(Boolean, default=False)          # 是否已使用
    attempt_count = Column(Integer, default=0)     # 验证尝试次数（防暴力破解）
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        # 邮箱+用途+未使用 复合索引，优化验证码查询性能
        Index("ix_vcode_email_purpose_used", "email", "purpose", "used"),
    )


class PostImage(Base):
    """帖子图片表"""
    __tablename__ = "post_images"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    url = Column(String(500), nullable=False)      # 图片访问路径/URL
    filename = Column(String(255), nullable=False) # 原始文件名
    size = Column(Integer, nullable=False)         # 文件大小（字节）
    order = Column(Integer, default=0)              # 图片顺序
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    post = relationship("Post", back_populates="images")


class PostVideo(Base):
    """帖子视频表"""
    __tablename__ = "post_videos"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    url = Column(String(500), nullable=False)           # 视频访问路径/URL
    filename = Column(String(255), nullable=False)      # 原始文件名
    size = Column(Integer, nullable=False)              # 文件大小（字节）
    duration = Column(Integer, nullable=False)          # 视频时长（秒）
    width = Column(Integer, nullable=True)              # 视频宽度（像素）
    height = Column(Integer, nullable=True)             # 视频高度（像素）
    thumbnail_url = Column(String(500), nullable=True)  # 视频封面图URL
    order = Column(Integer, default=0)                  # 视频顺序（与图片混合排序）
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    post = relationship("Post", back_populates="videos")


class Conversation(Base):
    """私信会话表（一对一）"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user2_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user1 = relationship("User", foreign_keys=[user1_id], back_populates="conversations_as_user1")
    user2 = relationship("User", foreign_keys=[user2_id], back_populates="conversations_as_user2")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at.desc()"
    )


class Message(Base):
    """私信消息表"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text")  # text/image/sticker/location
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)  # 位置信息

    # 关系
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    location = relationship("Location")


class GroupChat(Base):
    """群聊表"""
    __tablename__ = "group_chats"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)          # 群名称
    description = Column(String(500), nullable=True)     # 群描述
    avatar = Column(String(500), nullable=True)          # 群头像URL
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # 群主
    max_members = Column(Integer, default=200)           # 最大成员数
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship("GroupMember", back_populates="group_chat", cascade="all, delete-orphan")
    messages = relationship(
        "GroupMessage",
        back_populates="group_chat",
        cascade="all, delete-orphan",
        order_by="GroupMessage.created_at.desc()"
    )


class GroupMember(Base):
    """群成员表"""
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("group_chats.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), default="member", nullable=False)  # owner / admin / member
    joined_at = Column(DateTime, default=datetime.utcnow)
    muted = Column(Boolean, default=False)               # 是否免打扰

    # 关系
    group_chat = relationship("GroupChat", back_populates="members")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_member"),
        Index("ix_groupmember_user", "user_id", "group_id"),
    )


class GroupMessage(Base):
    """群聊消息表"""
    __tablename__ = "group_messages"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("group_chats.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text", nullable=False)  # text / image / sticker / location / system
    created_at = Column(DateTime, default=datetime.utcnow)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)  # 位置信息

    # 关系
    group_chat = relationship("GroupChat", back_populates="messages")
    sender = relationship("User")
    location = relationship("Location")


class Star(Base):
    """明星/艺人资料表"""
    __tablename__ = "stars"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)      # 明星姓名
    avatar = Column(String(500), nullable=True)                  # 头像URL
    cover_image = Column(String(500), nullable=True)             # 封面图URL
    description = Column(Text, nullable=True)                    # 简介
    birthday = Column(DateTime, nullable=True)                   # 生日
    gender = Column(String(10), nullable=True)                   # 性别
    nationality = Column(String(50), nullable=True)              # 国籍
    profession = Column(String(100), nullable=True)              # 职业
    debut_date = Column(DateTime, nullable=True)                 # 出道日期
    agency = Column(String(200), nullable=True)                  # 经纪公司
    social_links = Column(Text, nullable=True)                   # 社交链接（JSON格式）
    fan_count = Column(Integer, default=0)                       # 粉丝数（冗余字段）
    post_count = Column(Integer, default=0)                      # 帖子数（冗余字段）
    heat_score = Column(Integer, default=0)                      # 热度分数
    is_active = Column(Boolean, default=True)                    # 是否启用
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    posts = relationship("StarPost", back_populates="star", cascade="all, delete-orphan")
    followers = relationship("StarFollow", back_populates="star", cascade="all, delete-orphan")
    fans = relationship("StarFan", back_populates="star", cascade="all, delete-orphan")
    committee_members = relationship("DisciplineCommittee", back_populates="star", cascade="all, delete-orphan")
    checkins = relationship("FanCheckIn", back_populates="star", cascade="all, delete-orphan")
    fan_circle = relationship("FanCircle", back_populates="star", uselist=False, cascade="all, delete-orphan")
    fan_badges = relationship("FanBadge", back_populates="star", cascade="all, delete-orphan")


class StarPost(Base):
    """明星帖子关联表"""
    __tablename__ = "star_posts"

    id = Column(Integer, primary_key=True, index=True)
    star_id = Column(Integer, ForeignKey("stars.id", ondelete="CASCADE"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    star = relationship("Star", back_populates="posts")
    post = relationship("Post")

    __table_args__ = (
        UniqueConstraint("star_id", "post_id", name="uq_star_post"),
        Index("ix_starpost_star", "star_id", "created_at"),
    )


class StarFollow(Base):
    """明星粉丝关联表"""
    __tablename__ = "star_follows"

    id = Column(Integer, primary_key=True, index=True)
    star_id = Column(Integer, ForeignKey("stars.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    star = relationship("Star", back_populates="followers")
    user = relationship("User", back_populates="following_stars")

    __table_args__ = (
        UniqueConstraint("star_id", "user_id", name="uq_star_follow"),
        Index("ix_starfollow_star", "star_id", "created_at"),
        Index("ix_starfollow_user", "user_id", "created_at"),
    )


class StarFan(Base):
    """明星粉丝表（需申请审核）"""
    __tablename__ = "star_fans"

    id = Column(Integer, primary_key=True, index=True)
    star_id = Column(Integer, ForeignKey("stars.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending / approved / rejected
    fan_type = Column(String(20), default="casual", nullable=False)  # casual(路人粉) / true_fan(真爱粉) / diehard(死忠粉)
    apply_message = Column(String(500), nullable=True)  # 申请留言
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # 审核人
    reviewed_at = Column(DateTime, nullable=True)  # 审核时间
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    star = relationship("Star", back_populates="fans")
    user = relationship("User", foreign_keys=[user_id], back_populates="fan_applications")
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    __table_args__ = (
        UniqueConstraint("star_id", "user_id", name="uq_star_fan"),
        Index("ix_starfan_star_status", "star_id", "status", "created_at"),
        Index("ix_starfan_user", "user_id", "status"),
    )


class FanCheckIn(Base):
    """粉丝每日签到表"""
    __tablename__ = "fan_checkins"

    id = Column(Integer, primary_key=True, index=True)
    star_id = Column(Integer, ForeignKey("stars.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    checkin_date = Column(Date, nullable=False)  # 签到日期（根据04:00-次日04:00计算）
    checkin_time = Column(DateTime, default=datetime.utcnow)  # 实际签到时间
    consecutive_days = Column(Integer, default=1)  # 连续签到天数
    points = Column(Integer, default=1)  # 本次签到获得积分

    # 关系
    star = relationship("Star", back_populates="checkins")
    user = relationship("User", back_populates="checkins")

    __table_args__ = (
        UniqueConstraint("star_id", "user_id", "checkin_date", name="uq_fan_checkin"),
        Index("ix_checkin_star_date", "star_id", "checkin_date"),
        Index("ix_checkin_user", "user_id", "checkin_date"),
    )


class DisciplineCommittee(Base):
    """风纪委员会（粉丝模块内部，负责审核帖子）"""
    __tablename__ = "discipline_committees"

    id = Column(Integer, primary_key=True, index=True)
    star_id = Column(Integer, ForeignKey("stars.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending / approved / rejected / resigned
    role = Column(String(20), default="member", nullable=False)  # member / chairman
    apply_message = Column(String(500), nullable=True)       # 申请留言
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    star = relationship("Star", back_populates="committee_members")
    user = relationship("User", foreign_keys=[user_id], back_populates="committee_applications")
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    __table_args__ = (
        UniqueConstraint("star_id", "user_id", name="uq_discipline_committee"),
        Index("ix_dc_star_status", "star_id", "status", "created_at"),
        Index("ix_dc_user", "user_id", "status"),
    )


class Report(Base):
    """举报表"""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    reason = Column(String(50), nullable=False)        # 举报原因分类
    description = Column(String(1000), nullable=True)   # 详细描述
    status = Column(String(20), default="pending", nullable=False)  # pending / processing / resolved / dismissed
    handled_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # 处理人
    handle_result = Column(String(500), nullable=True)  # 处理结果说明
    handled_at = Column(DateTime, nullable=True)        # 处理时间
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    reporter = relationship("User", foreign_keys=[reporter_id], back_populates="reports_made")
    post = relationship("Post", back_populates="reports")
    handler = relationship("User", foreign_keys=[handled_by])

    __table_args__ = (
        Index("ix_report_post_status", "post_id", "status"),
        Index("ix_report_reporter", "reporter_id", "created_at"),
        Index("ix_report_status", "status", "created_at"),
    )


class FanCircle(Base):
    """粉丝圈 - 一个明星对应一个粉丝圈"""
    __tablename__ = "fan_circles"

    id = Column(Integer, primary_key=True, index=True)
    star_id = Column(Integer, ForeignKey("stars.id", ondelete="CASCADE"), nullable=False, unique=True)
    name = Column(String(100), nullable=False)  # 粉丝圈名称，如 "张三粉丝圈"
    description = Column(String(500), nullable=True)  # 粉丝圈简介
    avatar = Column(String(255), nullable=True)  # 粉丝圈头像
    banner = Column(String(255), nullable=True)  # 粉丝圈横幅
    member_count = Column(Integer, default=0)  # 成员数（粉丝数）
    post_count = Column(Integer, default=0)  # 帖子数
    status = Column(String(20), default="active")  # active / inactive
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    star = relationship("Star", back_populates="fan_circle")
    fans = relationship(
        "StarFan",
        primaryjoin="FanCircle.star_id == StarFan.star_id",
        foreign_keys=[star_id],
        viewonly=True
    )
    committee_members = relationship(
        "DisciplineCommittee",
        primaryjoin="FanCircle.star_id == DisciplineCommittee.star_id",
        foreign_keys=[star_id],
        viewonly=True
    )
    checkins = relationship(
        "FanCheckIn",
        primaryjoin="FanCircle.star_id == FanCheckIn.star_id",
        foreign_keys=[star_id],
        viewonly=True
    )
    photos = relationship("FanCirclePhoto", back_populates="circle", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_fancircle_status", "status", "member_count"),
    )


class FanBadge(Base):
    """粉丝牌 - 用户加入粉丝圈后获得的粉丝牌"""
    __tablename__ = "fan_badges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    star_id = Column(Integer, ForeignKey("stars.id", ondelete="CASCADE"), nullable=False)
    fan_type = Column(String(20), default="casual", nullable=False)  # casual / true_fan / diehard
    badge_name = Column(String(50), nullable=False)  # 粉丝牌名称，如 "张三的小粉丝"
    badge_level = Column(Integer, default=1)  # 粉丝牌等级
    badge_color = Column(String(20), nullable=True)  # 粉丝牌颜色
    is_displayed = Column(Boolean, default=False)  # 是否在个人主页展示
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="fan_badges")
    star = relationship("Star", back_populates="fan_badges")

    __table_args__ = (
        UniqueConstraint("user_id", "star_id", name="uq_user_star_badge"),
        Index("ix_fanbadge_user", "user_id", "is_displayed"),
    )


class FanCirclePhoto(Base):
    """粉丝圈共同空间照片"""
    __tablename__ = "fan_circle_photos"

    id = Column(Integer, primary_key=True, index=True)
    circle_id = Column(Integer, ForeignKey("fan_circles.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    url = Column(String(500), nullable=False)  # 图片URL
    filename = Column(String(255), nullable=True)  # 原始文件名
    description = Column(String(500), nullable=True)  # 照片描述
    status = Column(String(20), default="pending", nullable=False)  # pending/approved/rejected
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # 审核人
    reviewed_at = Column(DateTime, nullable=True)  # 审核时间
    reject_reason = Column(String(500), nullable=True)  # 驳回原因
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    circle = relationship("FanCircle", back_populates="photos")
    user = relationship("User", foreign_keys=[user_id], back_populates="circle_photos")
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    __table_args__ = (
        Index("ix_fancirclephoto_circle_status", "circle_id", "status", "created_at"),
        Index("ix_fancirclephoto_user", "user_id", "created_at"),
    )


class Sticker(Base):
    """表情包"""
    __tablename__ = "stickers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # 表情包名称
    url = Column(String(500), nullable=False)  # 表情包图片URL
    filename = Column(String(255), nullable=True)  # 原始文件名
    category = Column(String(50), default="default", nullable=True)  # 分类：default/emoji/custom
    width = Column(Integer, nullable=True)  # 图片宽度
    height = Column(Integer, nullable=True)  # 图片高度
    uploader_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # 上传者
    is_public = Column(Boolean, default=True)  # 是否公开（公开表情包所有用户可用）
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    uploader = relationship("User", foreign_keys=[uploader_id])

    __table_args__ = (
        Index("ix_sticker_category", "category", "created_at"),
    )


class UserSticker(Base):
    """用户表情包收藏"""
    __tablename__ = "user_stickers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sticker_id = Column(Integer, ForeignKey("stickers.id", ondelete="CASCADE"), nullable=False)
    sort_order = Column(Integer, default=0)  # 排序
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="user_stickers")
    sticker = relationship("Sticker")

    __table_args__ = (
        UniqueConstraint("user_id", "sticker_id", name="uq_user_sticker"),
        Index("ix_usersticker_user", "user_id", "sort_order"),
    )


class Location(Base):
    """位置信息"""
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    latitude = Column(Float, nullable=False)  # 纬度
    longitude = Column(Float, nullable=False)  # 经度
    name = Column(String(200), nullable=True)  # 位置名称（如：北京市朝阳区）
    address = Column(String(500), nullable=True)  # 详细地址
    poi_id = Column(String(100), nullable=True)  # 第三方POI ID（如高德地图POI ID）
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_location_coords", "latitude", "longitude"),
    )


class Tag(Base):
    """话题/标签表"""
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)  # 话题名称，如 "摄影"
    description = Column(String(200), nullable=True)  # 话题描述
    post_count = Column(Integer, default=0)           # 使用该话题的帖子数（冗余字段，方便查询）
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    posts = relationship("PostTag", back_populates="tag", cascade="all, delete-orphan")


class PostTag(Base):
    """帖子-话题关联表（多对多）"""
    __tablename__ = "post_tags"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    post = relationship("Post", back_populates="tags")
    tag = relationship("Tag", back_populates="posts")


class OauthAccount(Base):
    """第三方账号绑定表（v2 新增）

    用于记录本站用户与第三方平台（微信/抖音/支付宝）账号的绑定关系。
    - 同一第三方账号不可重复绑定到不同本站用户（UNIQUE(provider, oauth_uid)）
    - 一个本站用户可同时绑定多个平台（INDEX(user_id, provider)）
    """
    __tablename__ = "oauth_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(20), nullable=False)        # wechat / douyin / alipay
    oauth_uid = Column(String(100), nullable=False)      # 第三方用户唯一 ID
    access_token = Column(String(500), nullable=True)    # 第三方 access_token
    refresh_token = Column(String(500), nullable=True)   # 第三方 refresh_token（支付宝）
    expires_at = Column(DateTime, nullable=True)         # 第三方 token 过期时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="oauth_accounts")

    __table_args__ = (
        UniqueConstraint("provider", "oauth_uid", name="uq_provider_oauth_uid"),
        Index("ix_user_provider", "user_id", "provider"),
    )
