"""合规审核路由 — O4 存根版"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.auth.models import User
from app.creation import service as svc

router = APIRouter(prefix="/api/v1/review", tags=["review"])


@router.post("/{task_id}/approve")
async def review_approve(  # pragma: no cover
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """审核通过 — 存根版直接通过"""
    task = await svc.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    task.status = "APPROVED"
    await db.commit()
    return {"id": task.id, "status": "APPROVED", "reviewed": True}


@router.post("/{task_id}/reject")
async def review_reject(  # pragma: no cover
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """审核拒绝"""
    task = await svc.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    task.status = "REJECTED"
    await db.commit()
    return {"id": task.id, "status": "REJECTED", "reviewed": True}
