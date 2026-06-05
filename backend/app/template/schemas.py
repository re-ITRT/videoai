"""
灵感模板+策略因子 - Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ── Strategy Factor ─────────────────────

class StrategyFactorBase(BaseModel):
    name: str = Field(description="因子名称：痛点开场/场景化展示/产品特写")
    factor_type: str = Field(description="因子类型：hook / scene / narration / visual / ending")
    description: Optional[str] = None
    content: Dict[str, Any] = Field(description="因子具体内容：文案/画面描述/台词等")
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class StrategyFactorCreate(StrategyFactorBase):
    pass


class StrategyFactorUpdate(BaseModel):
    name: Optional[str] = None
    factor_type: Optional[str] = None
    description: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class StrategyFactorResponse(StrategyFactorBase):
    id: int
    user_id: str
    usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Inspiration Template ─────────────────

class InspirationTemplateBase(BaseModel):
    name: str = Field(description="模板名称")
    strategy: str = Field(description="创作策略：创作方法抽象描述")
    factors: Dict[str, Any] = Field(default_factory=dict, description="因子组合：不同环节使用的策略因子")
    reference_video_ids: List[int] = Field(default_factory=list, description="聚类来源的参考视频ID")
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    attribution_score: float = 0.0
    predicted_play_count: int = 2000


class InspirationTemplateCreate(InspirationTemplateBase):
    pass


class InspirationTemplateUpdate(BaseModel):
    name: Optional[str] = None
    strategy: Optional[str] = None
    factors: Optional[Dict[str, Any]] = None
    reference_video_ids: Optional[List[int]] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class InspirationTemplateResponse(InspirationTemplateBase):
    id: int
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    total: int
    items: List[InspirationTemplateResponse]


class FactorListResponse(BaseModel):
    total: int
    items: List[StrategyFactorResponse]


# ── Generate Script from Template ─────────

class GenerateFromTemplateRequest(BaseModel):
    """使用模板生成剧本请求"""
    template_id: int = Field(description="模板ID")
    product_info: Optional[Dict[str, Any]] = Field(default=None, description="产品信息，用于替换模板变量")
    custom_factors: Optional[Dict[str, int]] = Field(default=None, description="自定义因子选择：{环节: 因子ID}")
