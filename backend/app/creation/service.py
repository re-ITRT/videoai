"""创作模块业务层 — C10 多画幅导出"""
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.creation.models import VideoTask, TaskLog
from app.script.models import Script
from app.workers.workflow import call_workflow


# ── Task CRUD ─────────────────────────────

async def create_task(
    db: AsyncSession,
    user_id: int,
    product_info: dict,
    aspect_ratio: str = "9:16",
    auto_mode: bool = True,
    style: str | None = None,
) -> VideoTask:
    task = VideoTask(
        user_id=user_id,
        product_info=product_info,
        aspect_ratio=aspect_ratio,
        auto_mode=auto_mode,
        style=style,
        status="CREATED",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def get_task(db: AsyncSession, task_id: int) -> VideoTask | None:
    result = await db.execute(select(VideoTask).where(VideoTask.id == task_id))
    return result.scalar_one_or_none()


async def list_tasks(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 20) -> list[VideoTask]:
    result = await db.execute(
        select(VideoTask)
        .where(VideoTask.user_id == user_id)
        .order_by(VideoTask.id.desc())
        .offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def update_task_status(db: AsyncSession, task_id: int, status: str, error_msg: str | None = None) -> VideoTask | None:
    task = await get_task(db, task_id)
    if not task:
        return None
    task.status = status
    if error_msg:
        task.error_msg = error_msg
    await db.commit()
    await db.refresh(task)
    return task


# ── 导出 — C10 ────────────────────────────

async def export_video(
    db: AsyncSession,
    task_id: int,
    aspect_ratio: str | None = None,
) -> dict:
    """
    导出视频。如果指定 aspect_ratio 则覆盖任务原有的画幅设置。
    调用 video-compose 工作流完成最终合成。
    """
    task = await get_task(db, task_id)
    if not task:
        raise ValueError("任务不存在")

    target_ratio = aspect_ratio or task.aspect_ratio or "9:16"

    # 获取关联的剧本
    script = None
    if task.script_id:
        result = await db.execute(select(Script).where(Script.id == task.script_id))
        script = result.scalar_one_or_none()

    # 构造 video-compose 工作流 payload
    scenes = []
    if script and script.content:
        for scene in script.content.get("scenes", []):
            scenes.append({
                "scene_id": str(scene.get("id", 1)),
                "video_url": "",
                "audio_url": scene.get("audio_url"),
                "subtitle": scene.get("narration", ""),
                "duration": scene.get("duration", 5),
            })

    if not scenes:
        raise ValueError("无可导出的场景，请先生成剧本")

    payload = {
        "scenes": scenes,
        "aspect_ratio": target_ratio,
    }

    # 调用 video-compose 工作流
    try:
        result = await call_workflow("video-compose", payload)
    except Exception as e:
        raise RuntimeError(f"视频合成工作流调用失败: {e}")

    output_url = result.get("output_url", "")
    task.output_url = output_url
    task.aspect_ratio = target_ratio
    task.status = "EXPORTED"
    await db.commit()

    return {
        "task_id": task.id,
        "output_url": output_url,
        "aspect_ratio": target_ratio,
        "status": "EXPORTED",
    }


# ── TaskLog ───────────────────────────────

async def get_task_logs(db: AsyncSession, task_id: int) -> list[TaskLog]:
    result = await db.execute(
        select(TaskLog)
        .where(TaskLog.task_id == task_id)
        .order_by(TaskLog.id)
    )
    return list(result.scalars().all())
