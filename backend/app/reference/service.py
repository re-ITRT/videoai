"""
优质视频库 - 业务逻辑
"""
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.script.models import ReferenceVideo
from app.workers.workflow import call_workflow
from .schemas import VideoAnalyzeRequest


async def analyze_and_save_video(
    db: AsyncSession,
    user_id: str,
    request: VideoAnalyzeRequest
) -> ReferenceVideo:
    """
    调用video-analyze工作流分析视频，并保存结果到数据库
    ✅ 直接复用material-embed的scenes输出，无需重新处理视频
    """
    # 1. 调用扣子工作流分析（只传scenes，不处理视频本身）
    payload = {
        "scenes": [s.model_dump() for s in request.scenes],
        "source_platform": request.source_platform,
        "title": request.title,
        "category": request.category,
    }
    
    analysis_result = await call_workflow("video-analyze", payload)
    
    # 2. 解析分析结果
    hook_method = analysis_result.get("hook_method", "")
    selling_points = analysis_result.get("selling_points", [])
    storyboard = analysis_result.get("storyboard", [])
    style = analysis_result.get("style", "")
    analysis_report = analysis_result.get("analysis_report", {})
    
    # 3. 保存到数据库
    db_video = ReferenceVideo(
        user_id=user_id,
        source_platform=request.source_platform,
        source_url=request.source_url,
        title=request.title or analysis_result.get("title", ""),
        category=request.category or analysis_result.get("category", ""),
        hook_method=hook_method,
        selling_points=selling_points,
        storyboard=storyboard,
        style=style,
        analysis_report=analysis_report,
    )
    
    db.add(db_video)
    await db.commit()
    await db.refresh(db_video)
    
    return db_video


async def get_reference_videos(
    db: AsyncSession,
    user_id: str,
    category: Optional[str] = None,
    style: Optional[str] = None,
    source_platform: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
) -> Tuple[int, List[ReferenceVideo]]:
    """
    获取参考视频列表，支持筛选
    """
    query = select(ReferenceVideo).where(ReferenceVideo.user_id == user_id)
    
    if category:
        query = query.where(ReferenceVideo.category == category)
    if style:
        query = query.where(ReferenceVideo.style == style)
    if source_platform:
        query = query.where(ReferenceVideo.source_platform == source_platform)
    
    # 总数
    count_query = select(ReferenceVideo.id).where(ReferenceVideo.user_id == user_id)
    if category:
        count_query = count_query.where(ReferenceVideo.category == category)
    if style:
        count_query = count_query.where(ReferenceVideo.style == style)
    if source_platform:
        count_query = count_query.where(ReferenceVideo.source_platform == source_platform)
    
    count_result = await db.execute(count_query)
    total = len(count_result.all())
    
    # 分页查询
    query = query.order_by(desc(ReferenceVideo.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    videos = result.scalars().all()
    
    return total, list(videos)


async def get_reference_video_by_id(
    db: AsyncSession,
    video_id: int,
    user_id: str,
) -> Optional[ReferenceVideo]:
    """
    根据ID获取参考视频
    """
    query = select(ReferenceVideo).where(
        ReferenceVideo.id == video_id,
        ReferenceVideo.user_id == user_id,
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def delete_reference_video(
    db: AsyncSession,
    video_id: int,
    user_id: str,
) -> bool:
    """
    删除参考视频
    """
    video = await get_reference_video_by_id(db, video_id, user_id)
    if not video:
        return False
    
    await db.delete(video)
    await db.commit()
    return True
