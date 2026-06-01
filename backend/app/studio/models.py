"""工作流工作室数据模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class ProductInfo(Base):
    """产品介绍条目"""
    __tablename__ = "studio_products"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, nullable=False, index=True)
    title = Column(String(256), default="")
    content = Column(Text, default="")  # 完整产品介绍文案
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MaterialCollection(Base):
    """素材集合"""
    __tablename__ = "studio_material_collections"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, nullable=False, index=True)
    name = Column(String(256), default="素材集合")
    material_ids = Column(Text, default="[]")  # JSON array of material IDs
    threshold = Column(Integer, default=30)  # 相似度阈值 0-100
    tag_filter = Column(Text, default="[]")  # JSON array of tags
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VideoCollection(Base):
    """视频集合（多个视频片段）"""
    __tablename__ = "studio_video_collections"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, nullable=False, index=True)
    name = Column(String(256), default="视频集合")
    script_name = Column(String(256), default="")
    video_urls = Column(Text, default="[]")  # JSON array of video URLs
    created_at = Column(DateTime(timezone=True), server_default=func.now())
