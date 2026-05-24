from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base


class ReferenceVideo(Base):
    __tablename__ = "reference_videos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), nullable=False)
    source_platform = Column(String(32))  # FB / INS / TikTok / custom
    source_url = Column(Text)
    title = Column(String(256))
    category = Column(String(64))
    hook_method = Column(Text)  # Hook手法
    selling_points = Column(JSONB, default=[])  # 卖点
    storyboard = Column(JSONB, default=[])  # 分镜拆解
    style = Column(String(64))  # 风格
    analysis_report = Column(JSONB, default={})  # 完整结构化拆解报告
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InspirationTemplate(Base):
    __tablename__ = "inspiration_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), nullable=False)
    name = Column(String(256), nullable=False)
    strategy = Column(Text, nullable=False)  # 策略：创作方法抽象
    factors = Column(JSONB, default={})  # 因子：具体手段(开场/退场/画面/旁白)
    reference_video_ids = Column(JSONB, default=[])  # 聚类来源视频
    category = Column(String(64))
    tags = Column(JSONB, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Script(Base):
    __tablename__ = "scripts"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("video_tasks.id"), nullable=False)
    content = Column(JSONB, nullable=False)
    strategy = Column(String(64))  # 使用的策略
    factors = Column(JSONB, default={})  # 使用的因子
    reference_video_id = Column(Integer, ForeignKey("reference_videos.id"))
    template_id = Column(Integer, ForeignKey("inspiration_templates.id"))
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
