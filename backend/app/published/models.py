"""已生成视频 — 导出后持久化存储"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base


class PublishedVideo(Base):
    """已导出/发布的视频"""
    __tablename__ = "published_videos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    title = Column(String(256), default="未命名视频")
    video_url = Column(Text, default="")
    cover_url = Column(Text, default="")
    # 分析报告（video-analyze 输出）
    analysis_report = Column(JSONB, default={})
    hook_method = Column(Text, default="")
    selling_points = Column(JSONB, default=[])
    style = Column(String(64), default="")
    tags = Column(JSONB, default=[])
    scenes = Column(JSONB, default=[])
    # 播放量
    play_count = Column(Integer, default=2000)
    # 来源
    source_session_id = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
