"""素材嵌入详情查看"""
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.database import get_db
from app.core.deps import get_current_user
from app.auth.models import User
from app.material import service as svc
from app.material.models import MaterialSlice
from sqlalchemy import select

router = APIRouter(prefix="/api/v1/materials", tags=["materials"])


class EmbeddingResult(BaseModel):
    status: str = "pending"  # pending / done
    tags: list = []
    video_tags: list = []
    scenes: list = []
    text_content: str = ""
    text_embedding_dim: int = 0
    image_embedding_dim: int = 0


@router.get("/{material_id}/embedding")
async def get_material_embedding(
    material_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查看素材嵌入完整结果（标签、场景、向量维度等）"""
    material = await svc.get_material(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="素材不存在")

    # 从 material 的 tags 判断嵌入是否完成
    tags = list(material.tags) if material.tags else []
    has_tags = len(tags) > 0

    # 查询关联的素材切片（scenes）
    result = await db.execute(
        select(MaterialSlice).where(MaterialSlice.material_id == material_id).order_by(MaterialSlice.scene_id)
    )
    slices = result.scalars().all()
    scenes = [
        {
            "scene_id": s.scene_id,
            "time_range": s.time_range,
            "description": s.description,
            "script": s.script,
        }
        for s in slices
    ]

    return {
        "status": "done" if has_tags else "pending",
        "tags": tags,
        "video_tags": tags,  # material-embed 输出 video_tags 也存入 tags
        "scenes": scenes,
        "text_content": material.text_content or "",
        "text_embedding_dim": 1024 if has_tags else 0,
        "image_embedding_dim": 1024 if has_tags else 0,
    }
