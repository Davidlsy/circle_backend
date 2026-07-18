"""
视频处理工具函数
"""
import os
import io
import subprocess
import tempfile
from typing import Optional, Tuple
from pathlib import Path

from app.logging_config import logger

# 尝试导入 cv2，用于视频处理
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV (cv2) 未安装，视频处理功能将受限")


def get_video_info(file_path: str) -> Optional[dict]:
    """
    获取视频信息（时长、宽度、高度）

    Args:
        file_path: 视频文件路径

    Returns:
        dict: 包含 duration, width, height 的字典，失败返回 None
    """
    if CV2_AVAILABLE:
        return _get_video_info_cv2(file_path)
    else:
        return _get_video_info_ffmpeg(file_path)


def _get_video_info_cv2(file_path: str) -> Optional[dict]:
    """使用 OpenCV 获取视频信息"""
    try:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return None

        # 获取视频属性
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 计算时长
        duration = int(frame_count / fps) if fps > 0 else 0

        cap.release()

        return {
            "duration": duration,
            "width": width,
            "height": height
        }
    except Exception as e:
        logger.error(f"OpenCV 获取视频信息失败: {e}")
        return None


def _get_video_info_ffmpeg(file_path: str) -> Optional[dict]:
    """使用 FFmpeg 获取视频信息（备用方案）"""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,duration",
                "-of", "default=noprint_wrappers=1",
                file_path
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None

        info = {"duration": 0, "width": 0, "height": 0}
        for line in result.stdout.strip().split("\n"):
            if "=" in line:
                key, value = line.split("=", 1)
                if key == "duration":
                    info["duration"] = int(float(value))
                elif key == "width":
                    info["width"] = int(float(value))
                elif key == "height":
                    info["height"] = int(float(value))

        return info
    except Exception as e:
        logger.error(f"FFmpeg 获取视频信息失败: {e}")
        return None


def generate_thumbnail(video_path: str, output_path: str, width: int = 640) -> bool:
    """
    生成视频封面图（取第一帧）

    Args:
        video_path: 视频文件路径
        output_path: 封面图输出路径
        width: 封面图宽度

    Returns:
        bool: 是否成功
    """
    if CV2_AVAILABLE:
        return _generate_thumbnail_cv2(video_path, output_path, width)
    else:
        return _generate_thumbnail_ffmpeg(video_path, output_path, width)


def _generate_thumbnail_cv2(video_path: str, output_path: str, width: int) -> bool:
    """使用 OpenCV 生成封面图"""
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return False

        # 读取第一帧
        ret, frame = cap.read()
        if not ret:
            cap.release()
            return False

        # 计算缩放比例
        height, orig_width = frame.shape[:2]
        ratio = width / orig_width
        new_height = int(height * ratio)

        # 缩放
        resized = cv2.resize(frame, (width, new_height), interpolation=cv2.INTER_AREA)

        # 保存
        cv2.imwrite(output_path, resized)
        cap.release()

        return True
    except Exception as e:
        logger.error(f"OpenCV 生成封面图失败: {e}")
        return False


def _generate_thumbnail_ffmpeg(video_path: str, output_path: str, width: int) -> bool:
    """使用 FFmpeg 生成封面图（备用方案）"""
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-i", video_path,
                "-ss", "00:00:00",
                "-vframes", "1",
                "-vf", f"scale={width}:-1",
                "-y",
                output_path
            ],
            capture_output=True,
            timeout=30
        )
        return os.path.exists(output_path)
    except Exception as e:
        logger.error(f"FFmpeg 生成封面图失败: {e}")
        return False


def extract_frame_at_time(video_path: str, output_path: str, time_seconds: int, width: int = 640) -> bool:
    """
    从视频指定时间点提取帧作为封面

    Args:
        video_path: 视频文件路径
        output_path: 封面图输出路径
        time_seconds: 时间点（秒）
        width: 封面图宽度

    Returns:
        bool: 是否成功
    """
    if CV2_AVAILABLE:
        return _extract_frame_at_time_cv2(video_path, output_path, time_seconds, width)
    else:
        return _extract_frame_at_time_ffmpeg(video_path, output_path, time_seconds, width)


def _extract_frame_at_time_cv2(video_path: str, output_path: str, time_seconds: int, width: int) -> bool:
    """使用 OpenCV 从指定时间点提取帧"""
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return False

        # 获取视频属性
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = int(total_frames / fps) if fps > 0 else 0

        # 检查时间点是否有效
        if time_seconds > duration:
            time_seconds = duration

        # 计算目标帧位置
        target_frame = int(time_seconds * fps)

        # 设置到目标帧
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

        # 读取帧
        ret, frame = cap.read()
        if not ret:
            cap.release()
            return False

        # 计算缩放比例
        height, orig_width = frame.shape[:2]
        ratio = width / orig_width
        new_height = int(height * ratio)

        # 缩放
        resized = cv2.resize(frame, (width, new_height), interpolation=cv2.INTER_AREA)

        # 保存
        cv2.imwrite(output_path, resized)
        cap.release()

        return True
    except Exception as e:
        logger.error(f"OpenCV 提取视频帧失败: {e}")
        return False


def _extract_frame_at_time_ffmpeg(video_path: str, output_path: str, time_seconds: int, width: int) -> bool:
    """使用 FFmpeg 从指定时间点提取帧"""
    try:
        # 将秒转换为 HH:MM:SS 格式
        hours = time_seconds // 3600
        minutes = (time_seconds % 3600) // 60
        seconds = time_seconds % 60
        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        subprocess.run(
            [
                "ffmpeg",
                "-i", video_path,
                "-ss", time_str,
                "-vframes", "1",
                "-vf", f"scale={width}:-1",
                "-y",
                output_path
            ],
            capture_output=True,
            timeout=30
        )
        return os.path.exists(output_path)
    except Exception as e:
        logger.error(f"FFmpeg 提取视频帧失败: {e}")
        return False


def validate_video_content(content: bytes, max_duration: int = 300) -> Tuple[bool, str]:
    """
    验证视频内容有效性

    Args:
        content: 视频文件内容
        max_duration: 最大允许时长（秒）

    Returns:
        Tuple[bool, str]: (是否有效, 错误信息)
    """
    # 临时保存文件以验证
    with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        info = get_video_info(tmp_path)
        if not info:
            return False, "无法读取视频信息"

        if info["duration"] > max_duration:
            return False, f"视频时长超过限制（最大 {max_duration} 秒）"

        if info["duration"] <= 0:
            return False, "视频时长无效"

        return True, ""
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass


# 视频格式映射表（content_type -> 扩展名）
VIDEO_CONTENT_TYPE_TO_EXT = {
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
    "video/x-msvideo": ".avi",
}
