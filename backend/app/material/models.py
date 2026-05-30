from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    name = Column(String(256), nullable=False)
    description = Column(Text)
    category = Column(String(64))
    selling_points = Column(JSONB, default=[])
    style_tags = Column(JSONB, default=[])
    cover_url = Column(Text)
    status = Column(String(20), default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))
    material_type = Column(String(20), nullable=False)  # product / general / reference
    category = Column(String(64))
    input_type = Column(String(20), nullable=False)  # image / video
    image_hash = Column(String(128))
    image_url = Column(Text)
    video_url = Column(Text)
    text_content = Column(Text)
    embedding = Column(Vector(1024))  # 1024维向量
    tags = Column(JSONB, default=[])
    source = Column(String(64))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MaterialSlice(Base):
    __tablename__ = "material_slices"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id", ondelete="CASCADE"), nullable=False)
    slice_type = Column(String(20), nullable=False)  # video_scene / keyframe / audio_segment
    scene_id = Column(Integer)
    time_range = Column(String(32))
    description = Column(Text)
    script = Column(Text)
    image_url = Column(Text)
    embedding = Column(Vector(1024))
    tags = Column(JSONB, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
