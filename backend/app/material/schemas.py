"""素材模块 Schema"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Upload ────────────────────────────────

class MaterialUploadRequest(BaseModel):
    product_id: Optional[int] = None
    material_type: str  # product / general / reference
    input_type: str  # image / video
    image_url: Optional[str] = None
    text_content: Optional[str] = None
    source: str = "upload"
    # material-embed 工作流输出
    scenes: list[str] = Field(default_factory=list, description="material-embed 返回的 scenes JSON 字符串数组")
    video_tags: list[str] = Field(default_factory=list)


class MaterialUploadResponse(BaseModel):
    id: int
    material_type: str
    input_type: str
    image_url: Optional[str] = None
    text_content: Optional[str] = None
    source: str = "upload"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Material ──────────────────────────────

class MaterialResponse(BaseModel):
    id: int
    user_id: str
    product_id: Optional[int] = None
    material_type: str
    input_type: str
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    text_content: Optional[str] = None
    tags: list = []
    audio_features: dict = {}
    source: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Slice ─────────────────────────────────

class SliceCreateRequest(BaseModel):
    slice_type: str  # video_scene / keyframe / audio_segment
    scene_id: Optional[int] = None
    time_range: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None


class SliceResponse(BaseModel):
    id: int
    material_id: int
    slice_type: str
    scene_id: Optional[int] = None
    time_range: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    tags: list = []
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Search ────────────────────────────────

class MaterialSearchRequest(BaseModel):
    query: str
    product_id: Optional[int] = None
    threshold: float = 0.6
    max_results: int = 50
    search_level: str = "material"  # material / slice


class MaterialSearchResult(BaseModel):
    id: int
    similarity: float
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    text_content: Optional[str] = None
    tags: list = []
