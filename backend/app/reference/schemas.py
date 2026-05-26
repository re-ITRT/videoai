"""
优质视频库 - Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class VideoAnalyzeRequest(BaseModel):
    """视频分析请求"""
    source_url: str = Field(description="视频来源URL")
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
