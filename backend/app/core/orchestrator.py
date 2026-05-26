"""
创作编排器 — 状态机驱动 7 步工作流
"""
import time
import json
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.states import TaskState, WORKFLOW_STEPS, TRANSITIONS, EDITABLE_STATES
from app.core.ws_manager import manager
from app.creation.models import VideoTask, TaskLog
from app.workers.workflow import call_workflow

# 各工作流使用的模型名称
WORKFLOW_MODELS = {
    "material-embed": "doubao-embedding-vision-251215",
    "query-generate": "doubao-seed-2.0-pro",
    "material-search": "doubao-embedding-vision-251215",
    "script-generate": "doubao-seed-2.0-pro",
    "tts-generate": "doubao-seed-2.0-pro",
    "video-generate": "doubao-seedance-1.5-pro",
    "video-compose": "doubao-seed-2.0-pro",
}


async def run_next_step(db: AsyncSession, task: VideoTask, user_id: str):
    """
    执行任务的下一个步骤。
    支持自动模式（连续执行）和手动模式（单步执行）。
    """
    current_state = TaskState(task.status)

    # 找当前状态对应的下一个工作流
    next_state_name = None
    for src_state, dst_state in TRANSITIONS.items():
        if src_state.value == task.status:
            next_state_name = dst_state.value
            break

    if not next_state_name:
        return  # 已完成或无可执行步骤

    # 由目标状态名找工作流名
    workflow_name = None
    for step_state_name, wf_name, _ in WORKFLOW_STEPS:
        if step_state_name == next_state_name:
            workflow_name = wf_name
            break

    if not workflow_name:
        return

    # 标记为执行中
    task.status = workflow_name.upper().replace("-", "_")
    await db.commit()

    # 推送：开始执行
    await manager.broadcast_task_progress(
        user_id, task.id,
        state=task.status,
        workflow_name=workflow_name,
        editable=False,
    )

    # 记录日志
    log = TaskLog(task_id=task.id, step=workflow_name, status="started")
    db.add(log)
    await db.commit()

    start_time = time.time()

    try:
        # 构建 payload
        payload = build_payload(task, workflow_name)
        result = await call_workflow(workflow_name, payload)

        # 保存结果
        task.status = f"{workflow_name.upper().replace('-', '_')}_DONE"
        save_workflow_result(task, workflow_name, result)
        await db.commit()

        # 推送：完成
        editable = TaskState(task.status) in EDITABLE_STATES
        await manager.broadcast_task_progress(
            user_id, task.id,
            state=task.status,
            workflow_name=workflow_name,
            result=result,
            editable=editable,
        )

        # 更新日志
        duration_ms = int((time.time() - start_time) * 1000)
        log.status = "completed"
        log.duration_ms = duration_ms
        log.model_used = WORKFLOW_MODELS.get(workflow_name)
        await db.commit()

        # 自动模式下继续下一步
        if task.auto_mode and not editable:
            await run_next_step(db, task, user_id)

    except Exception as e:
        task.status = "FAILED"
        task.error_msg = str(e)
        await db.commit()

        log.status = "failed"
        log.error_msg = str(e)
        await db.commit()

        await manager.broadcast_task_progress(
            user_id, task.id,
            state="FAILED",
            workflow_name=workflow_name,
            result={"error": str(e)},
        )


def build_payload(task: VideoTask, workflow_name: str) -> dict:
    """根据工作流名称构造 payload"""
    if workflow_name == "material-embed":
        product_info = (task.product_info or {})
        return {
            "brief_description": product_info.get("name", ""),
            "image_url": product_info.get("cover_url", ""),
            "input_type": "image",
            "user_id": str(task.user_id),
            "product_id": product_info.get("id"),
            "material_type": "product",
        }
    elif workflow_name == "query-generate":
        return {
            "product_info": task.product_info or {},
            "video_style": task.style or "电商带货",
            "target_duration": task.duration or 15,
        }
    elif workflow_name == "material-search":
        return {"product_queries": [], "general_queries": []}
    elif workflow_name == "script-generate":
        return {
            "product_info": task.product_info or {},
            "video_style": task.style or "电商带货",
            "target_duration": task.duration or 15,
            "selected_materials": [],
            "mode": "auto" if task.auto_mode else "manual",
        }
    elif workflow_name == "tts-generate":
        return {"scenes": task.script_id or []}
    elif workflow_name == "video-generate":
        return {
            "task_id": str(task.id),
            "aspect_ratio": task.aspect_ratio or "9:16",
            "scenes": [],
        }
    elif workflow_name == "video-compose":
        return {
            "scenes": [],
            "aspect_ratio": task.aspect_ratio or "9:16",
        }
    return {}


def save_workflow_result(task: VideoTask, workflow_name: str, result: dict):
    """将工作流结果保存到 task 上"""
    if workflow_name == "script-generate":
        scenes = result.get("scenes", [])
        if scenes:
            # 创建脚本记录
            pass  # A 负责的模块
    elif workflow_name == "video-compose":
        task.output_url = result.get("output_url", "")
