from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


# ── 剧本生成 ──────────────────────────
class ScriptGenerateRequest(BaseModel):
    product_id: Optional[int] = None
    product_info: Optional[Dict[str, Any]] = None
    template_id: Optional[int] = None
    reference_video_id: Optional[int] = None
    strategy_id: Optional[int] = None
    factor_ids: List[int] = []
    num_variants: int = 1
    additional_instructions: Optional[str] = None
    aspect_ratio: str = "9:16"
    mode: str = "auto"
    target_duration: int = 15


class Scene(BaseModel):
    id: int
    order: int
    description: str
    narration: str
    dialogue: Optional[str] = None
    visual_style: Optional[str] = None
    camera_movement: Optional[str] = None
    bgm_type: Optional[str] = None
    duration: int = 5
    transition: Optional[str] = None
    material_slice_ids: List[int] = []


class ScriptGenerateResponse(BaseModel):
    id: int
    task_id: int
    title: str
    scenes: List[Scene]
    constraints: List[str]
    mode: str
    created_at: datetime


# ── 爆款视频分析 ──────────────────────────
class VideoAnalyzeRequest(BaseModel):
    video_url: str
    analysis_type: str = "full"  # full | quick


class StoryboardItem(BaseModel):
    time_range: str
    description: str
    camera_movement: Optional[str] = None


class VideoAnalyzeResponse(BaseModel):
    id: int
    video_url: str
    hook_method: str
    selling_points: List[str]
    storyboard: List[StoryboardItem]
    style: str
    bgm_type: str
    overall_rating: float
    created_at: datetime


# ── 分镜干预 ──────────────────────────
class SceneUpdateRequest(BaseModel):
    description: Optional[str] = None
    narration: Optional[str] = None
    duration: Optional[int] = None
    visual_style: Optional[str] = None
    factor_replacements: Dict[str, str] = {}


class FactorReplaceRequest(BaseModel):
    replacements: Dict[str, str]
