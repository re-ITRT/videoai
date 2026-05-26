"""创作模块路由 — C10 多画幅导出"""
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.auth.models import User
from app.creation.schemas import TaskCreateRequest
from app.creation import service as svc
from app.creation.models import VideoTask
from app.core.ws_manager import manager
from app.core.orchestrator import run_next_step
from app.core.states import EDITABLE_STATES, TaskState

router = APIRouter(prefix="/api/v1/tasks", tags=["creation"])


@router.post("")
async def create_task(
    request: TaskCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建视频任务"""
    task = await svc.create_task(
        db=db,
        user_id=current_user.id,
        product_info=request.product_info,
        aspect_ratio=request.aspect_ratio,
        auto_mode=request.auto_mode,
        style=request.style,
    )
    return {
        "id": task.id,
        "status": task.status,
        "aspect_ratio": task.aspect_ratio,
        "auto_mode": task.auto_mode,
        "created_at": task.created_at,
    }


@router.get("")
async def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """任务列表"""
    tasks = await svc.list_tasks(db, current_user.id, skip=skip, limit=limit)
    return [
        {
            "id": t.id,
            "status": t.status,
            "aspect_ratio": t.aspect_ratio,
            "auto_mode": t.auto_mode,
            "script_id": t.script_id,
            "created_at": t.created_at,
        }
        for t in tasks
    ]


@router.get("/{task_id}")
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """任务状态查询"""
    task = await svc.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {
        "id": task.id,
        "status": task.status,
        "aspect_ratio": task.aspect_ratio,
        "auto_mode": task.auto_mode,
        "product_info": task.product_info,
        "script_id": task.script_id,
        "output_url": task.output_url,
        "error_msg": task.error_msg,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


@router.get("/{task_id}/logs")
async def get_task_logs(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成过程追踪日志"""
    task = await svc.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    logs = await svc.get_task_logs(db, task_id)
    return [
        {
            "id": log.id,
            "step": log.step,
            "status": log.status,
            "model_used": log.model_used,
            "duration_ms": log.duration_ms,
            "created_at": log.created_at,
        }
        for log in logs
    ]


@router.post("/{task_id}/retry")
async def retry_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """重试失败步骤"""
    task = await svc.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    task.retry_count = (task.retry_count or 0) + 1
    task.status = "RETRYING"
    task.error_msg = None
    await db.commit()
    return {"id": task.id, "status": task.status, "retry_count": task.retry_count}


# ── C10 多画幅导出 ────────────────────────

@router.post("/{task_id}/export")
async def export_video(
    task_id: int,
    aspect_ratio: str | None = Query(None, description="画幅，如 9:16, 16:9, 1:1, 4:3"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """导出视频（多画幅）— C10"""
    try:
        result = await svc.export_video(db, task_id, aspect_ratio=aspect_ratio)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


# ── U4 WebSocket 进度推送 ────────────────

@router.websocket("/ws")
async def task_ws(ws: WebSocket):
    """WebSocket 实时进度 — 连接后按 task_id 订阅推送"""
    await ws.accept()
    try:
        data = await ws.receive_json()
        user_id = data.get("user_id", "unknown")
        await manager.connect(user_id, ws)
        await ws.send_json({"type": "connected", "user_id": user_id})

        while True:
            msg = await ws.receive_json()
            # 客户端可发心跳或查询
            if msg.get("type") == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        try:
            await manager.disconnect(user_id, ws)
        except Exception:
            pass


# ── 手动模式：用户确认，继续下一步 ────────

@router.post("/{task_id}/approve")
async def approve_step(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """用户审核中间结果后，确认继续执行下一步"""
    task = await svc.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    current = TaskState(task.status)
    if current not in EDITABLE_STATES:
        raise HTTPException(status_code=400, detail=f"当前状态 {task.status} 不允许手动确认")

    # 推进到下一步
    from app.core.states import TRANSITIONS
    next_state = TRANSITIONS.get(current)
    if next_state:
        task.status = next_state.value
        await db.commit()
        # 触发编排器继续
        await run_next_step(db, task, str(current_user.id))

    return {"id": task.id, "status": task.status}
