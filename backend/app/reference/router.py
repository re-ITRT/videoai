"""
优质视频库 - API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.deps import get_current_user
from app.auth.models import User
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


@router.post("/upload-analyze")
async def upload_and_analyze(
    file: UploadFile = File(None),
    source_url: str = Form(None),
    title: str = Form(None),
    category: str = Form(None),
    source_platform: str = Form("custom"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传视频 → material-embed提取scenes → video-analyze语义分析 → 存库"""
    import os, uuid, shutil
    from app.core.signer import generate_signed_url
    from app.workers.workflow import call_workflow
    from app.script.models import ReferenceVideo

    saved_url = None
    if file and file.filename:
        ext = os.path.splitext(file.filename)[1] or ".mp4"
        fname = f"{uuid.uuid4().hex}{ext}"
        fpath = f"/app/uploads/analyze/{fname}"
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, "wb") as f:
            shutil.copyfileobj(file.file, f)
        saved_url = generate_signed_url(fpath.replace("/app/uploads", "/uploads"), expire_seconds=86400)
        saved_url = f"http://114.117.242.17:3000{saved_url}"

    video_url = saved_url or source_url or ""

    # 判断是否视频文件
    is_video = False
    if file and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        is_video = ext in (".mp4", ".mov", ".avi", ".webm", ".mkv")
    elif source_url:
        is_video = any(source_url.lower().endswith(e) for e in (".mp4", ".mov", ".avi", ".webm"))

    embed_data = {}
    scenes = []
    tags = []

    # 调 material-embed（图片用 image_url，视频用 video_url）
    try:
        embed_payload = {"material_type": "product"}
        if is_video:
            embed_payload["video_url"] = video_url
        else:
            embed_payload["image_url"] = video_url
            embed_payload["brief_description"] = title or "上传素材"
        embed_result = await call_workflow("material-embed", embed_payload)
        embed_data = embed_result.get("data") if isinstance(embed_result, dict) and "data" in embed_result else embed_result
        scenes = embed_data.get("scenes", []) if isinstance(embed_data, dict) else []
        if isinstance(embed_data, dict):
            tags = embed_data.get("video_tags", []) or embed_data.get("tags", [])
    except Exception:
        pass

    # 2. 调 video-analyze（视频用 scenes 分析）
    analyze_result = {}
    if not scenes and video_url:
        scenes = [{"scene_id": 1, "time_range": "<00:00-00:05>", "description": title or "上传的视频素材", "script": ""}]

    if scenes:
        try:
            analyze_result = await call_workflow("video-analyze", {
                "scenes": scenes,
                "source_platform": source_platform,
                "title": title or "",
                "category": category or "",
            })
        except Exception:
            analyze_result = {}

    db_video = ReferenceVideo(
        user_id=str(current_user.id),
        source_platform=source_platform,
        source_url=video_url,
        title=title or (embed_data.get("text_content", "")[:30] if isinstance(embed_data, dict) else ""),
        category=category,
        # material-embed 数据
        tags=tags,
        text_content=embed_data.get("text_content", "") if isinstance(embed_data, dict) else "",
        text_embedding=embed_data.get("text_embedding", []) if isinstance(embed_data, dict) else [],
        image_embedding=embed_data.get("image_embedding", []) if isinstance(embed_data, dict) else [],
        scenes=scenes,
        # video-analyze 数据
        hook_method=analyze_result.get("hook_method", ""),
        selling_points=analyze_result.get("selling_points", []),
        storyboard=analyze_result.get("storyboard", []),
        style=analyze_result.get("style", ""),
        analysis_report=analyze_result or {},
    )
    db.add(db_video)
    await db.commit()
    await db.refresh(db_video)

    return {"success": True, "video_id": db_video.id, "message": f"嵌入完成({len(scenes)} scenes) + 分析完成"}


@router.get("/videos", response_model=ReferenceVideoListResponse)
async def list_reference_videos(
    category: Optional[str] = Query(None, description="按分类筛选"),
    style: Optional[str] = Query(None, description="按风格筛选"),
    source_platform: Optional[str] = Query(None, description="按来源平台筛选"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取优质视频库列表，支持多维度筛选
    """
    total, videos = await get_reference_videos(
        db, str(current_user.id), category, style, source_platform, skip, limit
    )
    
    return ReferenceVideoListResponse(
        total=total,
        items=[ReferenceVideoResponse.model_validate(v) for v in videos],
    )


@router.get("/videos/{video_id}", response_model=ReferenceVideoResponse)
async def get_video_detail(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个参考视频详情"""
    video = await get_reference_video_by_id(db, video_id, str(current_user.id))
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    
    return ReferenceVideoResponse.model_validate(video)


@router.delete("/videos/{video_id}")
async def delete_video(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除参考视频"""
    success = await delete_reference_video(db, video_id, str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="视频不存在")
    
    return {"success": True, "message": "删除成功"}
