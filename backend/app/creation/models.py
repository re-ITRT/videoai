from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base


class VideoTask(Base):
    __tablename__ = "video_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(32), nullable=False, default="CREATED")
    auto_mode = Column(Boolean, default=True)
    product_info = Column(JSONB, nullable=False)
    style = Column(String(64))
    duration = Column(Integer)
    script_id = Column(Integer, ForeignKey("scripts.id"))
    audio_url = Column(Text)
    video_urls = Column(JSONB, default=[])
    output_url = Column(Text)
    aspect_ratio = Column(String(8), default="9:16")  # 9:16 / 16:9
    error_msg = Column(Text)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TaskLog(Base):
    """生成过程追踪"""
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("video_tasks.id"), nullable=False)
    step = Column(String(32), nullable=False)  # material_embed / query_generate / ...
    status = Column(String(16), nullable=False)  # started / completed / failed
    duration_ms = Column(Integer)
    model_used = Column(String(64))
    tokens_consumed = Column(Integer)
    input_data = Column(JSONB, default={})
    output_data = Column(JSONB, default={})
    error_msg = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
