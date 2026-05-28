"""素材详情页面 — 查看嵌入状态和结果"""
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.database import get_db
from app.core.deps import get_current_user
from app.auth.models import User
from app.material import service as svc

router = APIRouter(prefix="/api/v1/materials", tags=["materials"])


class EmbeddingResult(BaseModel):
    status: str = "pending"  # pending / processing / done / failed
    tags: list = []
    video_tags: list = []
    scenes: list = []
    error: Optional[str] = None


@router.get("/{material_id}/embedding", response_model=EmbeddingResult)
async def get_material_embedding(
    material_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查看素材嵌入状态和结果"""
    material = await svc.get_material(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="素材不存在")

    # 从 material 字段中获取嵌入状态和结果
    # 这些信息由上传流程或异步任务写入
    from sqlalchemy import select, text
    
    # 检查是否有关联的 task_log 记录了嵌入过程
    from app.creation.models import TaskLog
    from sqlalchemy import select as sel
    result = await db.execute(
        sel(TaskLog).where(
            TaskLog.step == "material-embed",
            TaskLog.task_id == material_id,
        ).order_by(TaskLog.id.desc()).limit(1)
    )
    log = result.scalar_one_or_none()

    if log:
        return EmbeddingResult(
            status=log.status,
            tags=log.output_data.get("tags", []) if log.output_data else [],
            video_tags=log.output_data.get("video_tags", []) if log.output_data else [],
            scenes=log.output_data.get("scenes", []) if log.output_data else [],
        )

    return EmbeddingResult(status="pending")
