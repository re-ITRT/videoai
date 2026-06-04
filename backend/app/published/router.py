"""已生成视频 API — 导出/列表/播放量"""
import os, json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func, delete
from app.core.database import get_db
from app.core.deps import get_current_user
from app.auth.models import User
from app.published.models import PublishedVideo

router = APIRouter(prefix="/api/v1/published", tags=["published"])


@router.post("/export")
async def publish_video(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """导出视频：调 video-analyze 分析 → 存 published_videos"""
    from app.workers.workflow import call_workflow

    video_url = body.get("video_url", "")
    title = body.get("title", "未命名视频")
    source_session_id = body.get("session_id", 0)

    if not video_url:
        raise HTTPException(400, "video_url required")

    # 1. 调 material-embed 提取 scenes + tags
    scenes = []
    tags = []
    embed_data = {}
    try:
        embed_payload = {"material_type": "product", "video_url": video_url}
        embed_result = await call_workflow("material-embed", embed_payload)
        embed_data = embed_result.get("data") if isinstance(embed_result, dict) and "data" in embed_result else embed_result
        scenes = embed_data.get("scenes", []) if isinstance(embed_data, dict) else []
        if isinstance(embed_data, dict):
            tags = embed_data.get("video_tags", []) or embed_data.get("tags", [])
        print(f"[publish] material-embed got {len(scenes)} scenes, {len(tags)} tags")
    except Exception as e:
        print(f"[publish] material-embed failed: {e}")

    # 2. 调 video-analyze 分析
    analyze_result = {}
    if not scenes:
        scenes = [{"scene_id": 1, "time_range": "<00:00-00:05>", "description": title, "script": ""}]
    try:
        analyze_result = await call_workflow("video-analyze", {
            "scenes": scenes,
            "source_platform": "custom",
            "title": title,
            "category": "",
        })
    except Exception as e:
        print(f"[publish] video-analyze failed: {e}")

    # 合并 tags
    if isinstance(analyze_result, dict):
        analyze_tags = analyze_result.get("tags", [])
        if analyze_tags:
            tags = list(dict.fromkeys(tags + analyze_tags))

    pv = PublishedVideo(
        user_id=user.id,
        title=title,
        video_url=video_url,
        cover_url=body.get("cover_url", ""),
        analysis_report=analyze_result if isinstance(analyze_result, dict) else {},
        hook_method=analyze_result.get("hook_method", ""),
        selling_points=analyze_result.get("selling_points", []),
        style=analyze_result.get("style", ""),
        tags=tags,
        scenes=scenes,
        play_count=2000,
        source_session_id=source_session_id,
    )
    db.add(pv)
    await db.commit()
    await db.refresh(pv)

    return {"success": True, "id": pv.id, "video_url": video_url}


@router.get("/videos")
async def list_published(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query("created_at", regex="^(created_at|play_count)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取已生成视频列表"""
    from app.published.models import PublishedVideo

    order_col = getattr(PublishedVideo, sort)
    order_fn = order_col.desc() if order == "desc" else order_col.asc()

    count_q = select(sa_func.count()).where(PublishedVideo.user_id == user.id)
    total = (await db.execute(count_q)).scalar() or 0

    q = select(PublishedVideo).where(
        PublishedVideo.user_id == user.id
    ).order_by(order_fn).offset(skip).limit(limit)
    rows = (await db.execute(q)).scalars().all()

    items = []
    for r in rows:
        items.append({
            "id": r.id,
            "title": r.title,
            "video_url": r.video_url,
            "cover_url": r.cover_url,
            "play_count": r.play_count,
            "hook_method": r.hook_method,
            "style": r.style,
            "tags": r.tags or [],
            "analysis_report": r.analysis_report or {},
            "created_at": r.created_at.isoformat() if r.created_at else "",
        })

    return {"total": total, "items": items}


@router.post("/{video_id}/view")
async def increment_view(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """增加播放量"""
    from app.published.models import PublishedVideo

    r = await db.get(PublishedVideo, video_id)
    if not r or r.user_id != user.id:
        raise HTTPException(404, "视频不存在")

    r.play_count = (r.play_count or 0) + 1
    await db.commit()
    return {"play_count": r.play_count}


@router.put("/{video_id}/play-count")
async def update_published_play_count(
    video_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """设置已生成视频播放量"""
    r = await db.get(PublishedVideo, video_id)
    if not r or r.user_id != user.id:
        raise HTTPException(404, "视频不存在")
    r.play_count = body.get("play_count", 2000)
    await db.commit()
    return {"play_count": r.play_count}


@router.delete("/{video_id}")
async def delete_published(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除已生成视频"""
    from app.published.models import PublishedVideo

    r = await db.get(PublishedVideo, video_id)
    if not r or r.user_id != user.id:
        raise HTTPException(404, "视频不存在")

    await db.delete(r)
    await db.commit()
    return {"success": True}
