"""AI Agent 配置管理"""
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class UserAIConfig(Base):
    """用户AI配置"""
    __tablename__ = "user_ai_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)
    base_url = Column(String(512), nullable=False, default="https://api.openai.com/v1")
    api_key = Column(String(256), nullable=False)
    model = Column(String(128), nullable=False, default="gpt-4o")
    available_models = Column(Text, default="[]")  # JSON array
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AIConfigResponse(BaseModel):
    base_url: str
    model: str
    available_models: list = []

    class Config:
        from_attributes = True


class AIConfigUpdate(BaseModel):
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
