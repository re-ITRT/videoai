"""
优质视频库 - Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class Scene(BaseModel):
    """单个场景数据，与material-embed输出格式对齐"""
    scene_id: int = Field(description="场景ID")
    time_range: str = Field(description="时间范围，如 <00:00-00:03>")
    description: str = Field(description="画面内容描述")
    script: Optional[str] = Field(default=None, description="旁白/字幕内容")


class VideoAnalyzeRequest(BaseModel):
    """视频分析请求 - 直接复用material-embed的scenes输出，无需重新处理视频"""
    material_id: Optional[int] = Field(default=None, description="素材ID（可选，如果已存入素材库）")
    scenes: list[Scene] = Field(description="material-embed工作流输出的scenes数组")
    source_platform: Optional[str] = Field(default="custom", description="来源平台: FB/INS/TikTok/custom")
    title: Optional[str] = Field(default=None, description="视频标题")
    category: Optional[str] = Field(default=None, description="视频分类")


class ReferenceVideoResponse(BaseModel):
    """参考视频响应"""
    id: int
    user_id: str
    source_platform: Optional[str]
    source_url: Optional[str]
    title: Optional[str]
    category: Optional[str]
    hook_method: Optional[str]
    selling_points: Optional[List[str]]
    storyboard: Optional[List[Dict[str, Any]]]
    style: Optional[str]
    analysis_report: Optional[Dict[str, Any]]
    cover_url: Optional[str] = ""
    rhythm: float = 0.0
    scenes: Optional[List[Dict[str, Any]]] = []
    tags: Optional[List[str]] = []
    play_count: int = 2000
    audio_features: Optional[Dict[str, Any]] = {}
    created_at: datetime

    class Config:
        from_attributes = True


class ReferenceVideoListResponse(BaseModel):
    """参考视频列表响应"""
    total: int
    items: List[ReferenceVideoResponse]


class VideoAnalyzeResponse(BaseModel):
    """视频分析结果响应"""
    success: bool
    video_id: int
    message: str
