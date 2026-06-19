"""
Script API Router
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.script.schemas import ScriptGenerateRequest, ScriptGenerateResponse
from app.script.service import generate_script
from app.script.models import Script

router = APIRouter(prefix="/api/v1/scripts", tags=["scripts"])


@router.get("")
async def list_scripts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """剧本列表"""
    result = await db.execute(
        select(Script).order_by(Script.id.desc()).offset(skip).limit(limit)
    )
    scripts = result.scalars().all()
    return [
        {
            "id": s.id,
            "task_id": s.task_id,
            "strategy": s.strategy,
            "version": s.version,
            "created_at": s.created_at,
        }
        for s in scripts
    ]


@router.post("/generate", response_model=ScriptGenerateResponse)
async def api_generate_script(request: ScriptGenerateRequest):
    """
    生成剧本

    - **product_info**: 产品信息（必填）
    - **target_duration**: 目标时长（秒）
    - **mode**: 生成模式 - auto/imitation/template
    - **aspect_ratio**: 画幅比例 - 9:16/16:9/1:1/4:3
    """
    try:
        return await generate_script(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
