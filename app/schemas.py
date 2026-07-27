from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List


# ─── 用户相关 ───

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = None
    phone: Optional[str] = None
    nickname: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    nickname: Optional[str] = Field(None, max_length=50)
    avatar_url: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    political_status: Optional[str] = Field(None, pattern="^(masses|league|party)$", description="政治面貌：masses(群众)/league(共青团员)/party(中共党员)")


class UserPublic(BaseModel):
    id: int
    username: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    political_status: Optional[str] = "masses"
    created_at: datetime

    class Config:
        from_attributes = True


# ─── 举报相关 ───

# 举报原因分类
REPORT_REASONS = [
    "垃圾广告", "色情低俗", "虚假信息", "人身攻击",
    "侵犯版权", "违法违规", "恶意刷屏", "其他"
]


class ReportCreate(BaseModel):
    """提交举报"""
    post_id: int = Field(..., ge=1, description="被举报的帖子ID")
    reason: str = Field(..., description="举报原因分类")
    description: Optional[str] = Field(None, max_length=1000, description="详细描述")


class ReportHandleRequest(BaseModel):
    """处理举报"""
    status: str = Field(..., pattern="^(resolved|dismissed)$", description="处理结果：resolved(成立)/dismissed(不成立)")
    handle_result: Optional[str] = Field(None, max_length=500, description="处理结果说明")


class ReportPublic(BaseModel):
    """举报信息"""
    id: int
    reporter_id: int
    post_id: int
    reason: str
    description: Optional[str] = None
    status: str
    handled_by: Optional[int] = None
    handle_result: Optional[str] = None
    handled_at: Optional[datetime] = None
    created_at: datetime
    reporter: Optional[UserPublic] = None
    handler: Optional[UserPublic] = None

    class Config:
        from_attributes = True


class ReportList(BaseModel):
    """举报列表"""
    reports: List[ReportPublic]
    total: int
    page: int
    page_size: int


class ReportReasonsResponse(BaseModel):
    """举报原因列表"""
    reasons: List[str]


# ─── 粉丝签到相关 ───

class FanCheckInPublic(BaseModel):
    """签到记录"""
    id: int
    star_id: int
    user_id: int
    checkin_date: date
    checkin_time: datetime
    consecutive_days: int
    points: int

    class Config:
        from_attributes = True


class FanCheckInResponse(BaseModel):
    """签到响应"""
    msg: str
    checkin: FanCheckInPublic
    total_days: int  # 累计签到天数
    consecutive_days: int  # 连续签到天数
    today_points: int  # 本次获得积分


class FanCheckInStats(BaseModel):
    """签到统计"""
    total_days: int  # 累计签到天数
    consecutive_days: int  # 连续签到天数
    total_points: int  # 累计积分
    today_checked: bool  # 今日是否已签到
    today_checkin_time: Optional[datetime] = None  # 今日签到时间


class FanCheckInRankItem(BaseModel):
    """签到排行榜项"""
    rank: int
    user: UserPublic
    total_days: int
    consecutive_days: int


class FanCheckInCalendar(BaseModel):
    """签到日历"""
    year: int
    month: int
    checked_dates: List[str]  # 已签到日期列表，格式 "YYYY-MM-DD"


# ─── 粉丝圈相关 ───

class FanCirclePublic(BaseModel):
    """粉丝圈公开信息"""
    id: int
    star_id: int
    name: str
    description: Optional[str] = None
    avatar: Optional[str] = None
    banner: Optional[str] = None
    member_count: int = 0
    post_count: int = 0
    status: str = "active"
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FanCircleDetail(FanCirclePublic):
    """粉丝圈详情"""
    star: Optional[StarPublic] = None


class FanCircleList(BaseModel):
    """粉丝圈列表"""
    circles: List[FanCirclePublic]
    total: int
    page: int
    page_size: int


class FanCircleCreate(BaseModel):
    """创建粉丝圈"""
    star_id: int
    name: str
    description: Optional[str] = None
    avatar: Optional[str] = None
    banner: Optional[str] = None


class FanCircleUpdate(BaseModel):
    """更新粉丝圈"""
    name: Optional[str] = None
    description: Optional[str] = None
    avatar: Optional[str] = None
    banner: Optional[str] = None
    status: Optional[str] = None


# ─── 政治面貌相关 ───

POLITICAL_STATUS_OPTIONS = {
    "masses": "群众",
    "league": "共青团员",
    "party": "中共党员"
}


# ─── 粉丝牌相关 ───

# 粉丝牌配置：根据粉丝类型对应的称号和颜色
BADGE_CONFIG = {
    "casual": {
        "title": "路人粉",
        "badge_name_template": "{star_name}的路人粉",
        "color": "#808080",  # 灰色
        "level": 1
    },
    "true_fan": {
        "title": "真爱粉",
        "badge_name_template": "{star_name}的真爱粉",
        "color": "#FF69B4",  # 粉色
        "level": 2
    },
    "diehard": {
        "title": "死忠粉",
        "badge_name_template": "{star_name}的死忠粉",
        "color": "#FFD700",  # 金色
        "level": 3
    }
}


class FanBadgePublic(BaseModel):
    """粉丝牌公开信息"""
    id: int
    user_id: int
    star_id: int
    fan_type: str
    badge_name: str
    badge_level: int
    badge_color: Optional[str] = None
    is_displayed: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    star: Optional[StarPublic] = None

    class Config:
        from_attributes = True


class FanBadgeList(BaseModel):
    """粉丝牌列表"""
    badges: List[FanBadgePublic]
    total: int
    page: int
    page_size: int


class FanBadgeSetDisplayRequest(BaseModel):
    """设置展示粉丝牌请求"""
    badge_id: int


class UserWithDisplayBadge(BaseModel):
    """包含展示粉丝牌的用户信息"""
    id: int
    username: str
    display_badge: Optional[FanBadgePublic] = None


# ─── 位置相关 ───

class LocationPublic(BaseModel):
    """位置信息"""
    id: int
    latitude: float
    longitude: float
    name: Optional[str] = None
    address: Optional[str] = None
    poi_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LocationCreate(BaseModel):
    """创建位置信息"""
    latitude: float = Field(..., ge=-90, le=90, description="纬度")
    longitude: float = Field(..., ge=-180, le=180, description="经度")
    name: Optional[str] = Field(None, max_length=200, description="位置名称")
    address: Optional[str] = Field(None, max_length=500, description="详细地址")
    poi_id: Optional[str] = Field(None, max_length=100, description="POI ID")


# ─── 表情包相关 ───

class StickerPublic(BaseModel):
    """表情包公开信息"""
    id: int
    name: str
    url: str
    filename: Optional[str] = None
    category: Optional[str] = "default"
    width: Optional[int] = None
    height: Optional[int] = None
    is_public: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class StickerList(BaseModel):
    """表情包列表"""
    stickers: List[StickerPublic]
    total: int


class UserStickerPublic(BaseModel):
    """用户收藏的表情包"""
    id: int
    sticker_id: int
    sort_order: int = 0
    sticker: Optional[StickerPublic] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserStickerList(BaseModel):
    """用户表情包收藏列表"""
    stickers: List[UserStickerPublic]
    total: int


# 用户表情包收藏上限
MAX_USER_STICKERS = 100


# ─── 粉丝圈共同空间照片相关 ───

class FanCirclePhotoPublic(BaseModel):
    """粉丝圈照片公开信息"""
    id: int
    circle_id: int
    user_id: int
    url: str
    filename: Optional[str] = None
    description: Optional[str] = None
    status: str = "pending"
    created_at: datetime
    user: Optional[UserPublic] = None

    class Config:
        from_attributes = True


class FanCirclePhotoUpload(BaseModel):
    """上传照片请求"""
    description: Optional[str] = Field(None, max_length=500, description="照片描述")


class FanCirclePhotoList(BaseModel):
    """照片列表"""
    photos: List[FanCirclePhotoPublic]
    total: int
    page: int
    page_size: int


class FanCirclePhotoAuditRequest(BaseModel):
    """审核照片请求"""
    status: str = Field(..., pattern="^(approved|rejected)$", description="审核结果")
    reject_reason: Optional[str] = Field(None, max_length=500, description="驳回原因")


# ─── 风纪委员会相关 ───

class DCApplyRequest(BaseModel):
    """申请加入风纪委员会"""
    apply_message: Optional[str] = Field(None, max_length=500, description="申请留言")


class DCReviewRequest(BaseModel):
    """审核风纪委员会申请"""
    status: str = Field(..., pattern="^(approved|rejected)$")
    role: str = Field("member", pattern="^(member|chairman)$", description="分配角色")


class DCPublic(BaseModel):
    """风纪委员会成员信息"""
    id: int
    star_id: int
    user_id: int
    status: str
    role: str
    apply_message: Optional[str] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    user: Optional[UserPublic] = None
    reviewer: Optional[UserPublic] = None

    class Config:
        from_attributes = True


class DCList(BaseModel):
    """风纪委员会成员列表"""
    members: List[DCPublic]
    total: int
    page: int
    page_size: int


class MyDCApplicationPublic(BaseModel):
    """我的风纪委员会申请"""
    id: int
    star_id: int
    user_id: int
    status: str
    role: str
    apply_message: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    star: Optional[StarPublic] = None

    class Config:
        from_attributes = True


class UserProfile(UserPublic):
    """用户公开资料（含粉丝数/关注数）"""
    follower_count: int = 0
    following_count: int = 0


# ─── 认证相关 ───

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


# ─── 通用响应 ───

class Msg(BaseModel):
    msg: str


# ─── 图片相关（前置声明，避免 forward ref） ───

class PostImagePublic(BaseModel):
    id: int
    post_id: int
    url: str
    filename: str
    size: int
    order: int
    created_at: datetime

    class Config:
        from_attributes = True


class PostVideoPublic(BaseModel):
    """帖子视频 Schema"""
    id: int
    post_id: int
    url: str
    filename: str
    size: int
    duration: int                    # 视频时长（秒）
    width: Optional[int] = None      # 视频宽度
    height: Optional[int] = None     # 视频高度
    thumbnail_url: Optional[str] = None  # 视频封面图URL
    order: int
    created_at: datetime

    class Config:
        from_attributes = True


class VideoUploadResponse(BaseModel):
    """视频上传响应"""
    msg: str
    video: Optional[PostVideoPublic] = None


class VideoDeleteResponse(BaseModel):
    """视频删除响应"""
    msg: str


class VideoThumbnailUpdateRequest(BaseModel):
    """更新视频封面请求"""
    time_seconds: Optional[int] = Field(None, ge=0, description="从视频中截取封面的时间点（秒），不传则使用上传的图片")


class VideoThumbnailUpdateResponse(BaseModel):
    """更新视频封面响应"""
    msg: str
    thumbnail_url: str


# ─── 帖子相关 ───

class CommentBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class CommentCreate(CommentBase):
    post_id: int
    parent_id: Optional[int] = None


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class CommentPublic(BaseModel):
    id: int
    content: str
    author_id: int
    post_id: int
    parent_id: Optional[int] = None
    status: str = "pending"
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CommentWithAuthor(CommentPublic):
    author: UserPublic
    like_count: int = 0          # 评论点赞数
    is_liked: bool = False       # 当前用户是否点赞


class CommentLikeResponse(BaseModel):
    """评论点赞响应"""
    msg: str
    is_liked: bool
    like_count: int


class PostBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    content_format: str = Field("markdown", pattern="^(markdown|html|plain)$", description="内容格式：markdown / html / plain")


class PostCreate(PostBase):
    is_published: bool = True
    star_id: int = Field(..., ge=1, description="关联的明星ID，必填")


class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    content_format: Optional[str] = Field(None, pattern="^(markdown|html|plain)$")
    is_published: Optional[bool] = None


class PostPublic(BaseModel):
    id: int
    title: str
    content: str                          # 原始内容
    content_format: str = "markdown"      # 内容格式：markdown / html / plain
    content_html: str = ""                # 渲染后的 HTML
    content_summary: str = ""             # 纯文本摘要（最多 200 字）
    author_id: int
    is_published: bool
    status: str = "pending"   # pending / approved / rejected
    view_count: int
    is_pinned: bool = False   # 是否置顶
    is_featured: bool = False  # 是否加精
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PostWithAuthor(PostPublic):
    author: UserPublic


class PostDetail(PostPublic):
    author: UserPublic
    star: Optional[StarPublic] = None  # 关联的明星信息
    comment_count: int = 0
    like_count: int = 0
    is_liked: bool = False
    collection_count: int = 0
    is_collected: bool = False
    images: List[PostImagePublic] = []
    videos: List[PostVideoPublic] = []  # 新增视频列表
    tags: List[TagPublic] = []
    status: str = "pending"


class PostList(BaseModel):
    posts: List[PostDetail]
    total: int
    page: int
    page_size: int


class LikeResponse(BaseModel):
    msg: str
    liked: bool
    like_count: int


# ─── 关注相关 ───

class FollowResponse(BaseModel):
    msg: str
    following: bool
    follower_count: int
    following_count: int


class UserWithCounts(UserPublic):
    follower_count: int = 0
    following_count: int = 0


class UserList(BaseModel):
    users: List[UserWithCounts]
    total: int


class FollowStatus(BaseModel):
    is_following: bool
    is_followed_by: bool
    follower_count: int
    following_count: int


# ─── 找回密码相关 ───

class ForgotPasswordRequest(BaseModel):
    username: str = Field(..., description="用户名或注册邮箱")


class ForgotPasswordResponse(BaseModel):
    msg: str
    code: str = Field(..., description="6位验证码")
    expires_in_seconds: int


class ResetPasswordRequest(BaseModel):
    email: str = Field(..., description="用户邮箱")
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6, max_length=128)


# ─── 图片上传相关 ───

class ImageUploadResponse(BaseModel):
    images: List[PostImagePublic]
    uploaded_count: int
    post_id: int


class ImageDeleteResponse(BaseModel):
    msg: str
    remaining_count: int


# ─── 收藏相关 ───

class CollectionResponse(BaseModel):
    msg: str
    collected: bool
    collection_count: int


class CollectionList(BaseModel):
    posts: List[PostDetail]
    total: int
    page: int
    page_size: int


# ─── 私信相关 ───

class ConversationCreate(BaseModel):
    """发起或获取一个会话"""
    target_user_id: int


class ConversationPublic(BaseModel):
    id: int
    user1_id: int
    user2_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConversationListItem(BaseModel):
    """会话列表项：含对方用户信息、最后一条消息、未读数"""
    id: int
    other_user: UserPublic
    last_message: Optional["MessagePublic"] = None
    unread_count: int = 0
    updated_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationList(BaseModel):
    conversations: List[ConversationListItem]
    total: int


class MessageSend(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    message_type: Optional[str] = Field("text", pattern="^(text|image|sticker|location)$")
    location: Optional[LocationCreate] = None  # 当 message_type=location 时必填


class MessagePublic(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    content: str
    message_type: Optional[str] = "text"
    is_read: bool
    location: Optional[LocationPublic] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MessageWithSender(MessagePublic):
    sender: UserPublic


class MessageList(BaseModel):
    messages: List[MessageWithSender]
    total: int
    page: int
    page_size: int


class MarkReadResponse(BaseModel):
    msg: str
    read_count: int


# ─── 标签/话题相关 ───

class TagPublic(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    post_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class TagList(BaseModel):
    tags: List[TagPublic]
    total: int


class PostTagPublic(BaseModel):
    id: int
    tag_id: int
    tag: TagPublic
    created_at: datetime

    class Config:
        from_attributes = True


class AddTagsRequest(BaseModel):
    tag_ids: List[int] = Field(..., min_length=1, max_length=9, description="最多9个标签ID")


# ─── 内容审核相关 ───

class AuditRequest(BaseModel):
    status: str = Field(..., description="审核状态: approved 或 rejected")
    reason: Optional[str] = Field(None, max_length=200, description="驳回原因（可选）")


class AuditResponse(BaseModel):
    msg: str
    id: int
    status: str


class PendingPostItem(BaseModel):
    id: int
    title: str
    content: str
    author: UserPublic
    created_at: datetime

    class Config:
        from_attributes = True


class PendingPostList(BaseModel):
    posts: List[PendingPostItem]
    total: int
    page: int
    page_size: int


class PendingCommentItem(BaseModel):
    id: int
    content: str
    author: UserPublic
    post_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PendingCommentList(BaseModel):
    comments: List[PendingCommentItem]
    total: int
    page: int
    page_size: int


# ─── 群聊相关 ───

class GroupChatCreate(BaseModel):
    """创建群聊"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    max_members: int = Field(200, ge=2, le=500)


class GroupChatUpdate(BaseModel):
    """更新群聊信息"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    max_members: Optional[int] = Field(None, ge=2, le=500)


class GroupChatPublic(BaseModel):
    """群聊信息"""
    id: int
    name: str
    description: Optional[str] = None
    avatar: Optional[str] = None
    owner_id: Optional[int] = None
    max_members: int
    member_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GroupMemberPublic(BaseModel):
    """群成员信息"""
    id: int
    group_id: int
    user_id: int
    role: str
    joined_at: datetime
    muted: bool = False
    user: Optional[UserPublic] = None

    class Config:
        from_attributes = True


class GroupMessagePublic(BaseModel):
    """群聊消息"""
    id: int
    group_id: int
    sender_id: int
    content: str
    message_type: str = "text"
    location: Optional[LocationPublic] = None
    created_at: datetime
    sender: Optional[UserPublic] = None

    class Config:
        from_attributes = True


class GroupMessageCreate(BaseModel):
    """发送群消息"""
    content: str = Field(..., min_length=1)
    message_type: str = Field("text", pattern="^(text|image|sticker|location)$")
    location: Optional[LocationCreate] = None  # 当 message_type=location 时必填


class GroupInviteRequest(BaseModel):
    """邀请成员"""
    user_ids: List[int] = Field(..., min_length=1, max_length=50)


class GroupRoleUpdate(BaseModel):
    """更新成员角色"""
    role: str = Field(..., pattern="^(admin|member)$")


# ─── 明星相关 ───

class StarCreate(BaseModel):
    """创建明星资料"""
    name: str = Field(..., min_length=1, max_length=100)
    avatar: Optional[str] = Field(None, max_length=500)
    cover_image: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    birthday: Optional[datetime] = None
    gender: Optional[str] = Field(None, pattern="^(男|女|其他)$")
    nationality: Optional[str] = Field(None, max_length=50)
    profession: Optional[str] = Field(None, max_length=100)
    debut_date: Optional[datetime] = None
    agency: Optional[str] = Field(None, max_length=200)
    social_links: Optional[str] = None


class StarUpdate(BaseModel):
    """更新明星资料"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    avatar: Optional[str] = Field(None, max_length=500)
    cover_image: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    birthday: Optional[datetime] = None
    gender: Optional[str] = Field(None, pattern="^(男|女|其他)$")
    nationality: Optional[str] = Field(None, max_length=50)
    profession: Optional[str] = Field(None, max_length=100)
    debut_date: Optional[datetime] = None
    agency: Optional[str] = Field(None, max_length=200)
    social_links: Optional[str] = None
    is_active: Optional[bool] = None


class StarPublic(BaseModel):
    """明星资料公开信息"""
    id: int
    name: str
    avatar: Optional[str] = None
    cover_image: Optional[str] = None
    description: Optional[str] = None
    birthday: Optional[datetime] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    profession: Optional[str] = None
    debut_date: Optional[datetime] = None
    agency: Optional[str] = None
    social_links: Optional[str] = None
    fan_count: int = 0
    post_count: int = 0
    heat_score: int = 0
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StarList(BaseModel):
    """明星列表"""
    stars: List[StarPublic]
    total: int
    page: int
    page_size: int


class StarPostCreate(BaseModel):
    """创建明星关联帖子"""
    star_id: int
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    content_format: str = Field("markdown", pattern="^(markdown|html|plain)$")


class StarPostPublic(BaseModel):
    """明星帖子关联"""
    id: int
    star_id: int
    post_id: int
    created_at: datetime
    post: Optional[PostPublic] = None

    class Config:
        from_attributes = True


class StarRankingItem(BaseModel):
    """明星排行榜项"""
    rank: int
    star: StarPublic
    fan_count: int
    post_count: int
    heat_score: int


# ─── 粉丝相关 ───

class StarFollowResponse(BaseModel):
    """关注/取消关注响应"""
    msg: str
    is_following: bool
    fan_count: int


class StarFollowerPublic(BaseModel):
    """粉丝信息"""
    id: int
    star_id: int
    user_id: int
    created_at: datetime
    user: Optional[UserPublic] = None

    class Config:
        from_attributes = True


class UserFollowingStarPublic(BaseModel):
    """用户关注的明星"""
    id: int
    star_id: int
    user_id: int
    created_at: datetime
    star: Optional[StarPublic] = None

    class Config:
        from_attributes = True


# ─── 粉丝相关（申请-审核制） ───

class StarFanApplyRequest(BaseModel):
    """申请成为粉丝"""
    apply_message: Optional[str] = Field(None, max_length=500, description="申请留言")


class StarFanReviewRequest(BaseModel):
    """审核粉丝申请"""
    status: str = Field(..., pattern="^(approved|rejected)$", description="审核结果")
    fan_type: str = Field("casual", pattern="^(casual|true_fan|diehard)$", description="粉丝类型")
    review_message: Optional[str] = Field(None, max_length=500, description="审核回复")


class StarFanPublic(BaseModel):
    """粉丝信息"""
    id: int
    star_id: int
    user_id: int
    status: str  # pending / approved / rejected
    fan_type: str = "casual"  # casual(路人粉) / true_fan(真爱粉) / diehard(死忠粉)
    apply_message: Optional[str] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    user: Optional[UserPublic] = None
    reviewer: Optional[UserPublic] = None

    class Config:
        from_attributes = True


class StarFanList(BaseModel):
    """粉丝列表"""
    fans: List[StarFanPublic]
    total: int
    page: int
    page_size: int


class MyFanApplicationPublic(BaseModel):
    """我的粉丝申请"""
    id: int
    star_id: int
    user_id: int
    status: str
    fan_type: str = "casual"
    apply_message: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    star: Optional[StarPublic] = None

    class Config:
        from_attributes = True


# ─── 第三方登录（v2 新增） ───

class OAuthAuthorizeResponse(BaseModel):
    """获取授权 URL 响应"""
    authorize_url: str


class OAuthCallbackRequest(BaseModel):
    """OAuth 登录回调请求

    code 字段：
    - 微信/抖音：从授权页 query 中获取的 code
    - 支付宝：从授权页 query 中获取的 auth_code
    - Mock 模式：mock_{provider}_{account_index}_{timestamp}
    """
    code: str = Field(..., min_length=1, max_length=500)
    state: str = Field(..., min_length=1, max_length=200)


class OAuthBindRequest(BaseModel):
    """OAuth 账号绑定请求（与回调结构一致，但需登录态）"""
    code: str = Field(..., min_length=1, max_length=500)
    state: str = Field(..., min_length=1, max_length=200)


class OAuthBindingPublic(BaseModel):
    """已绑定的第三方账号信息"""
    provider: str
    oauth_uid: str
    created_at: datetime

    class Config:
        from_attributes = True


class OAuthRegisterRequest(BaseModel):
    """OAuth 第三方注册请求"""
    code: str = Field(..., min_length=1, max_length=500)
    state: str = Field(..., min_length=1, max_length=200)
    username: str = Field(None, min_length=1, max_length=50)


class OAuthRegisterResponse(BaseModel):
    """OAuth 注册/登录响应"""
    access_token: str
    token_type: str = "bearer"
    is_new_user: bool = False
