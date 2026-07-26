-- ============================================================
-- 粉丝社群平台 / Fan Community Platform - 数据库 Schema
-- 数据库类型: SQLite (开发) / MySQL (生产)
-- 创建时间: 2026-04-17
-- ============================================================

-- -----------------------------------------------------------
-- 1. users 用户表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        VARCHAR(50)  NOT NULL UNIQUE,
    email           VARCHAR(100) UNIQUE,
    phone           VARCHAR(20)  UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    nickname        VARCHAR(50),
    avatar_url      VARCHAR(500),
    bio             VARCHAR(200),
    is_active       BOOLEAN      NOT NULL DEFAULT 1,
    is_superuser    BOOLEAN      NOT NULL DEFAULT 0,
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_users_username ON users(username);
CREATE INDEX IF NOT EXISTS ix_users_email    ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_phone     ON users(phone);


-- -----------------------------------------------------------
-- 2. posts 帖子表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS posts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         VARCHAR(200) NOT NULL,
    content       TEXT         NOT NULL,
    author_id     INTEGER      NOT NULL,
    is_published  BOOLEAN      NOT NULL DEFAULT 1,
    view_count    INTEGER      NOT NULL DEFAULT 0,
    status       VARCHAR(20)  NOT NULL DEFAULT 'pending',  -- pending/approved/rejected
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_posts_title     ON posts(title);
CREATE INDEX IF NOT EXISTS ix_posts_author_id ON posts(author_id);
CREATE INDEX IF NOT EXISTS ix_posts_created   ON posts(created_at DESC);


-- -----------------------------------------------------------
-- 3. comments 评论表（支持回复嵌套）
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS comments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    content     TEXT        NOT NULL,
    author_id   INTEGER     NOT NULL,
    post_id     INTEGER     NOT NULL,
    parent_id   INTEGER,
    status      VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending/approved/rejected
    created_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (author_id) REFERENCES users(id)   ON DELETE CASCADE,
    FOREIGN KEY (post_id)   REFERENCES posts(id)  ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES comments(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_comments_post_id    ON comments(post_id);
CREATE INDEX IF NOT EXISTS ix_comments_author_id  ON comments(author_id);
CREATE INDEX IF NOT EXISTS ix_comments_parent_id  ON comments(parent_id);


-- -----------------------------------------------------------
-- 4. likes 点赞表（用户-帖子 多对多关联）
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS likes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    post_id     INTEGER NOT NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,

    -- 防止重复点赞
    UNIQUE(user_id, post_id)
);

CREATE INDEX IF NOT EXISTS ix_likes_user_id ON likes(user_id);
CREATE INDEX IF NOT EXISTS ix_likes_post_id ON likes(post_id);


-- -----------------------------------------------------------
-- 5. follows 关注关系表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS follows (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    follower_id  INTEGER NOT NULL,  -- 谁关注
    following_id INTEGER NOT NULL,  -- 关注谁
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (follower_id)  REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (following_id) REFERENCES users(id) ON DELETE CASCADE,

    UNIQUE(follower_id, following_id)
);

CREATE INDEX IF NOT EXISTS ix_follows_follower  ON follows(follower_id);
CREATE INDEX IF NOT EXISTS ix_follows_following ON follows(following_id);


-- -----------------------------------------------------------
-- 6. verification_codes 验证码表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS verification_codes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    email      VARCHAR(100)    NOT NULL,
    phone      VARCHAR(20),
    code       VARCHAR(6)      NOT NULL,   -- bcrypt 哈希存储
    purpose    VARCHAR(20)     NOT NULL DEFAULT 'reset_password',
    expires_at DATETIME        NOT NULL,
    used       BOOLEAN         NOT NULL DEFAULT 0,
    created_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_vc_email   ON verification_codes(email);
CREATE INDEX IF NOT EXISTS ix_vc_purpose ON verification_codes(purpose);


-- -----------------------------------------------------------
-- 7. post_images 帖子图片表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS post_images (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id   INTEGER      NOT NULL,
    url       VARCHAR(500) NOT NULL,  -- 访问路径，如 /uploads/xxx.jpg
    filename  VARCHAR(255) NOT NULL,  -- 原始文件名
    size      INTEGER      NOT NULL,  -- 文件大小（字节）
    `order`   INTEGER      NOT NULL DEFAULT 0,
    created_at DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_img_post_id ON post_images(post_id);


-- -----------------------------------------------------------
-- 8. collections 收藏表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS collections (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    post_id    INTEGER NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,

    UNIQUE(user_id, post_id)
);

CREATE INDEX IF NOT EXISTS ix_collections_user_id ON collections(user_id);
CREATE INDEX IF NOT EXISTS ix_collections_post_id ON collections(post_id);


-- -----------------------------------------------------------
-- 9. conversations 私信会话表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user1_id   INTEGER NOT NULL,   -- 会话双方，user1_id < user2_id 保证唯一性
    user2_id   INTEGER NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user1_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (user2_id) REFERENCES users(id) ON DELETE CASCADE,

    UNIQUE(user1_id, user2_id)
);

CREATE INDEX IF NOT EXISTS ix_conv_user1 ON conversations(user1_id);
CREATE INDEX IF NOT EXISTS ix_conv_user2 ON conversations(user2_id);


-- -----------------------------------------------------------
-- 10. messages 私信消息表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    sender_id       INTEGER NOT NULL,
    content         TEXT    NOT NULL,
    is_read         BOOLEAN NOT NULL DEFAULT 0,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id)       REFERENCES users(id)        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_msg_conv_id   ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS ix_msg_sender   ON messages(sender_id);
CREATE INDEX IF NOT EXISTS ix_msg_read     ON messages(is_read);


-- -----------------------------------------------------------
-- 11. tags 话题/标签表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS tags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(50)  NOT NULL UNIQUE,
    description VARCHAR(200),
    post_count  INTEGER      NOT NULL DEFAULT 0,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_tag_name ON tags(name);


-- -----------------------------------------------------------
-- 12. post_tags 帖子-话题关联表（多对多）
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS post_tags (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id    INTEGER NOT NULL,
    tag_id     INTEGER NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id)  REFERENCES tags(id)  ON DELETE CASCADE,

    UNIQUE(post_id, tag_id)
);
CREATE INDEX IF NOT EXISTS ix_pt_post_id ON post_tags(post_id);
CREATE INDEX IF NOT EXISTS ix_pt_tag_id  ON post_tags(tag_id);


-- ============================================================
-- 查询示例 / Sample Queries
-- ============================================================

-- 获取帖子列表（含作者信息、评论数、点赞数）
-- SELECT
--     p.*,
--     u.username,
--     u.nickname,
--     u.avatar_url,
--     COUNT(DISTINCT c.id)       AS comment_count,
--     COUNT(DISTINCT l.id)       AS like_count
-- FROM posts p
-- LEFT JOIN users   u ON p.author_id = u.id
-- LEFT JOIN comments c ON p.id = c.post_id
-- LEFT JOIN likes   l ON p.id = l.post_id
-- WHERE p.is_published = 1
-- GROUP BY p.id
-- ORDER BY p.created_at DESC;

-- 获取评论树（含回复）
-- WITH RECURSIVE comment_tree AS (
--     SELECT id, content, author_id, post_id, parent_id, created_at, 0 AS depth
--     FROM comments WHERE parent_id IS NULL
--     UNION ALL
--     SELECT c.id, c.content, c.author_id, c.post_id, c.parent_id, c.created_at, ct.depth + 1
--     FROM comments c
--     JOIN comment_tree ct ON c.parent_id = ct.id
-- )
-- SELECT * FROM comment_tree WHERE post_id = ?;
