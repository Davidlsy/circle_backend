# 更新日志 v1.0.53

## 版本信息
- **版本号**: v1.0.53
- **发布日期**: 2026-05-14
- **更新类型**: 功能新增

## 更新概述

本次更新新增**粉丝每日签到打卡功能**，签到时间窗口为**当日 04:00 至次日 04:00**，支持连续签到奖励、签到日历、排行榜等功能。

---

## 签到时间规则

| 时间段 | 归属日期 |
|--------|----------|
| 04:00 - 23:59:59 | 当天 |
| 00:00 - 03:59:59 | 前一天 |

**示例**:
- 1月1日 05:00 签到 → 归属 1月1日
- 1月2日 02:00 签到 → 归属 1月1日（跨天签到）

---

## 新增功能

### 1. 每日签到

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 签到打卡 | POST | `/stars/{id}/checkin` | 粉丝每日签到 | 已通过的粉丝 |

#### 1.1 连续签到奖励

| 连续天数 | 积分奖励 |
|----------|----------|
| 1-2 天 | 1 分 |
| 3-6 天 | 2 分 |
| 7-29 天 | 3 分 |
| 30+ 天 | 5 分 |

#### 1.2 返回示例

```json
{
  "msg": "签到成功！",
  "checkin": {
    "id": 1,
    "star_id": 1,
    "user_id": 2,
    "checkin_date": "2026-05-14",
    "checkin_time": "2026-05-14T08:30:00",
    "consecutive_days": 7,
    "points": 3
  },
  "total_days": 15,
  "consecutive_days": 7,
  "today_points": 3
}
```

---

### 2. 签到统计

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 签到状态 | GET | `/stars/{id}/checkin/status` | 我的签到统计 | 已通过的粉丝 |

#### 2.1 返回示例

```json
{
  "total_days": 15,
  "consecutive_days": 7,
  "total_points": 35,
  "today_checked": true,
  "today_checkin_time": "2026-05-14T08:30:00"
}
```

---

### 3. 签到日历

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 签到日历 | GET | `/stars/{id}/checkin/calendar` | 某月已签到日期 | 已通过的粉丝 |

#### 3.1 参数

- `year`: 年份（默认当年）
- `month`: 月份（默认当月）

#### 3.2 返回示例

```json
{
  "year": 2026,
  "month": 5,
  "checked_dates": ["2026-05-01", "2026-05-02", "2026-05-14"]
}
```

---

### 4. 签到排行榜

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 排行榜 | GET | `/stars/{id}/checkin/rank` | 签到排行榜 | 公开 |

#### 4.1 参数

- `rank_type`: 排行类型
  - `consecutive`（默认）- 按连续签到天数
  - `total` - 按累计签到天数
- `limit`: 返回数量（默认 20，最大 100）

#### 4.2 返回示例

```json
[
  {
    "rank": 1,
    "user": {"id": 1, "username": "user1", ...},
    "total_days": 100,
    "consecutive_days": 30
  }
]
```

---

### 5. 签到历史

| 接口 | 方法 | 路径 | 功能说明 | 权限 |
|------|------|------|----------|------|
| 签到历史 | GET | `/stars/{id}/checkin/history` | 我的签到记录 | 已通过的粉丝 |

#### 5.1 参数

- `page`: 页码（默认 1）
- `page_size`: 每页数量（默认 20）

---

## 数据模型

### 新增模型

| 模型 | 说明 | 主要字段 |
|------|------|----------|
| FanCheckIn | 粉丝签到 | star_id, user_id, checkin_date, checkin_time, consecutive_days, points |

### 字段说明

| 字段 | 说明 |
|------|------|
| `checkin_date` | 签到归属日期（根据04:00规则计算） |
| `checkin_time` | 实际签到时间 |
| `consecutive_days` | 连续签到天数 |
| `points` | 本次签到获得积分 |

### 索引优化

| 索引 | 说明 |
|------|------|
| `uq_fan_checkin` | 明星+用户+日期 唯一约束（每日只能签到一次） |
| `ix_checkin_star_date` | 明星+日期（快速查询某明星某日签到） |
| `ix_checkin_user` | 用户+日期（快速查询用户签到历史） |

---

## 文件变更

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `app/routers/checkin_router.py` | 签到路由（5 个接口） |

### 修改文件

| 文件路径 | 变更说明 |
|----------|----------|
| `app/models.py` | 新增 FanCheckIn 模型，Star/User 添加关系 |
| `app/schemas.py` | 新增签到相关 Schema（5 个） |
| `app/main.py` | 注册签到路由，更新版本号至 1.0.53 |

---

## 数据库迁移

```bash
alembic revision --autogenerate -m "add_fan_checkin_table"
alembic upgrade head
```

**新增表**:
- `fan_checkins` - 粉丝签到表

---

## API 统计

| 模块 | 原接口数 | 新接口数 | 总计 |
|------|----------|----------|------|
| 签到模块 | 0 | 5 | 5 |
| **项目总计** | 106 | 5 | **111** |

---

## 使用示例

### 每日签到
```bash
curl -X POST "http://localhost:8000/stars/1/checkin" \
  -H "Authorization: Bearer FAN_TOKEN"
```

### 查看签到状态
```bash
curl "http://localhost:8000/stars/1/checkin/status" \
  -H "Authorization: Bearer FAN_TOKEN"
```

### 查看签到日历
```bash
curl "http://localhost:8000/stars/1/checkin/calendar?year=2026&month=5" \
  -H "Authorization: Bearer FAN_TOKEN"
```

### 查看排行榜
```bash
# 连续签到榜
curl "http://localhost:8000/stars/1/checkin/rank?rank_type=consecutive&limit=10"

# 累计签到榜
curl "http://localhost:8000/stars/1/checkin/rank?rank_type=total&limit=10"
```

### 查看签到历史
```bash
curl "http://localhost:8000/stars/1/checkin/history?page=1&page_size=20" \
  -H "Authorization: Bearer FAN_TOKEN"
```

---

## 验证清单

- [x] FanCheckIn 数据模型
- [x] 签到时间窗口计算（04:00-次日04:00）
- [x] 连续签到天数计算
- [x] 连续签到奖励积分
- [x] 每日只能签到一次（唯一约束）
- [x] 签到接口
- [x] 签到统计接口
- [x] 签到日历接口
- [x] 签到排行榜（连续/累计）
- [x] 签到历史接口
- [x] 仅已通过的粉丝可签到
- [x] 复合索引优化
- [x] 更新版本号

---

**更新者**: 开发团队  
**审核状态**: ✅ 已通过
