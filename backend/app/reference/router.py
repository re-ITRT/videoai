"""
优质视频库 - API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from .schemas import (
    VideoAnalyzeRequest,
    VideoAnalyzeResponse,
    ReferenceVideoResponse,
    ReferenceVideoListResponse,
)
from .service import (
    analyze_and_save_video,
    get_reference_videos,
    get_reference_video_by_id,
    delete_reference_video,
)

router = APIRouter(prefix="/api/v1/reference", tags=["reference"])

# TODO: 替换为真实的用户认证
DEFAULT_USER_ID = "dev_user"


@router.post("/analyze", response_model=VideoAnalyzeResponse)
async def analyze_video(
    request: VideoAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    分析视频并保存到优质视频库
    
    - 调用video-analyze工作流进行爆款拆解
    - 保存Hook手法、卖点、分镜、风格等结构化数据
    """
    try:
        video = await analyze_and_save_video(db, DEFAULT_USER_ID, request)
        return VideoAnalyzeResponse(
            success=True,
            video_id=video.id,
            message=f"视频分析完成，已保存到优质视频库",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"视频分析失败: {str(e)}")


@router.get("/videos", response_model=ReferenceVideoListResponse)
async def list_reference_videos(
    category: Optional[str] = Query(None, description="按分类筛选"),
    style: Optional[str] = Query(None, description="按风格筛选"),
    source_platform: Optional[str] = Query(None, description="按来源平台筛选"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取优质视频库列表，支持多维度筛选
    
    - 按分类筛选（美妆、数码、食品等）
    - 按风格筛选（口播、测评、剧情等）
    - 按来源平台筛选（FB、INS、TikTok等）
    """
    total, videos = await get_reference_videos(
        db, DEFAULT_USER_ID, category, style, source_platform, skip, limit
    )
    
    return ReferenceVideoListResponse(
        total=total,
        items=[ReferenceVideoResponse.model_validate(v) for v in videos],
    )


@router.get("/videos/{video_id}", response_model=ReferenceVideoResponse)
async def get_video_detail(
    video_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取单个参考视频详情"""
    video = await get_reference_video_by_id(db, video_id, DEFAULT_USER_ID)
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    
    return ReferenceVideoResponse.model_validate(video)


@router.delete("/videos/{video_id}")
async def delete_video(
    video_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除参考视频"""
    success = await delete_reference_video(db, video_id, DEFAULT_USER_ID)
    if not success:
        raise HTTPException(status_code=404, detail="视频不存在")
    
    return {"success": True, "message": "删除成功"}
