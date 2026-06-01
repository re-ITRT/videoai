"""工作流配置管理"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class WorkflowConfig(Base):
    """工作流配置（每个用户每个工作流一条记录）"""
    __tablename__ = "workflow_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    workflow_name = Column(String(64), nullable=False)
    config = Column(Text, default="{}")  # JSON: {api_key, base_url, model, ...}
    enabled = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("user_id", "workflow_name"),)


class WorkflowConfigResponse(BaseModel):
    workflow_name: str
    config: dict = {}
    enabled: bool = True

    class Config:
        from_attributes = True


class WorkflowConfigUpdate(BaseModel):
    config: Optional[dict] = None
    enabled: Optional[bool] = None


# ── 可用本地工作流清单 ────────────────

AVAILABLE_WORKFLOWS = {
    "script-generate": {
        "name": "剧本生成",
        "description": "根据产品信息和素材生成结构化带货剧本",
        "fields": [
            {"key": "api_key", "label": "API Key", "type": "password", "placeholder": "sk-..."},
            {"key": "base_url", "label": "API 地址", "type": "text", "placeholder": "https://api.deepseek.com/v1"},
            {"key": "model", "label": "模型名称", "type": "text", "placeholder": "deepseek-v4-flash"},
            {"key": "temperature", "label": "温度 (0-1)", "type": "text", "placeholder": "0.8"},
        ],
    },
    "video-generate": {
        "name": "视频生成",
        "description": "本地直接调用火山方舟 Doubao-Seedance-1.5-pro 生成视频片段，不走 Coze 工作流",
        "fields": [
            {"key": "api_key", "label": "火山方舟 API Key", "type": "password", "placeholder": "ark-..."},
            {"key": "base_url", "label": "API 地址（固定）", "type": "text", "placeholder": "https://ark.cn-beijing.volces.com/api/v3", "disabled": True},
            {"key": "model", "label": "模型（固定）", "type": "text", "placeholder": "ep-20260514120705-pqv86", "disabled": True},
        ],
    },
}
