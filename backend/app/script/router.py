from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.script.schemas import (
    ScriptGenerateRequest,
    ScriptGenerateResponse,
    VideoAnalyzeRequest,
    VideoAnalyzeResponse,
    SceneUpdateRequest,
)
from app.script.service import generate_script, analyze_video, update_scene

router = APIRouter(prefix="/api/v1/scripts", tags=["scripts"])


# ──────────────────────────────────────────
# 🔥 核心接口：生成剧本
# ──────────────────────────────────────────
@router.post("/generate", response_model=ScriptGenerateResponse)
async def api_generate_script(
    request: ScriptGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    生成带货视频剧本
    - 支持模板模式、仿写模式、自动模式
    - 所有AI逻辑由扣子 script-generate 工作流实现
    """
    try:
        return await generate_script(db, request, str(current_user.id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成剧本失败: {str(e)}")


# ──────────────────────────────────────────
# 爆款视频分析
# ──────────────────────────────────────────
@router.post("/analyze", response_model=VideoAnalyzeResponse)
async def api_analyze_video(
    request: VideoAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    分析爆款视频，输出结构化拆解报告
    调用扣子 video-analyze 工作流
    """
    try:
        return await analyze_video(db, request, str(current_user.id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


# ──────────────────────────────────────────
# 分镜干预：更新单个分镜
# ──────────────────────────────────────────
@router.put("/{script_id}/scenes/{scene_id}")
async def api_update_scene(
    script_id: int,
    scene_id: int,
    update: SceneUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    更新剧本的单个分镜
    支持修改描述、旁白、时长、替换风格因子
    """
    try:
        return await update_scene(db, script_id, scene_id, update.dict(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
