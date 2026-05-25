from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.workers.workflow import call_workflow
from app.script.models import Script, ReferenceVideo, InspirationTemplate
from app.script.schemas import (
    ScriptGenerateRequest,
    ScriptGenerateResponse,
    Scene,
    VideoAnalyzeRequest,
    VideoAnalyzeResponse,
    StoryboardItem,
)


async def generate_script(
    db: AsyncSession,
    request: ScriptGenerateRequest,
    user_id: str,
) -> ScriptGenerateResponse:
    workflow_payload = {
        "product_info": request.product_info or {},
        "style": request.additional_instructions or "",
        "video_style": request.additional_instructions or "电商带货",
        "target_duration": request.target_duration,
        "selected_materials": [],
        "mode": request.mode,
    }

    if request.template_id:
        template = await db.get(InspirationTemplate, request.template_id)
        if template:
            workflow_payload["strategy"] = template.strategy
            workflow_payload["factors"] = template.factors

    if request.reference_video_id:
        video = await db.get(ReferenceVideo, request.reference_video_id)
        if video:
            workflow_payload["reference_analysis"] = video.analysis_report

    workflow_result = await call_workflow("script-generate", workflow_payload)

    scenes_data = workflow_result.get("scenes", [])
    scenes = [
        Scene(
            id=i+1,
            order=i+1,
            description=scene.get("description", ""),
            narration=scene.get("narration", ""),
            dialogue=scene.get("dialogue"),
            visual_style=scene.get("visual_style"),
            camera_movement=scene.get("camera_movement"),
            bgm_type=scene.get("bgm_type"),
            duration=scene.get("duration", 5),
            transition=scene.get("transition"),
            material_slice_ids=scene.get("material_slice_ids", []),
        )
        for i, scene in enumerate(scenes_data)
    ]

    db_script = Script(
        task_id=0,
        content={"scenes": [s.model_dump() for s in scenes]},
        strategy=request.additional_instructions,
        factors={},
        reference_video_id=request.reference_video_id,
        template_id=request.template_id,
    )
    db.add(db_script)
    await db.commit()
    await db.refresh(db_script)

    return ScriptGenerateResponse(
        id=db_script.id,
        task_id=db_script.task_id,
        title=workflow_result.get("title", "带货视频剧本"),
        scenes=scenes,
        constraints=workflow_result.get("constraints", [f"时长≤{request.target_duration}s"]),
        mode=request.mode,
        created_at=db_script.created_at,
    )


async def analyze_video(db, request, user_id):
    raise NotImplementedError("视频分析功能待实现")


async def update_scene(db, script_id, scene_id, update_data):
    raise NotImplementedError("分镜更新功能待实现")
