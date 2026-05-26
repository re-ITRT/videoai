"""
Script service - 剧本生成业务逻辑
"""
from typing import Dict, Any, List
from app.workers.workflow import call_workflow
from app.script.schemas import ScriptGenerateRequest, ScriptGenerateResponse, Scene


async def generate_script(request: ScriptGenerateRequest) -> ScriptGenerateResponse:
    """
    生成剧本 - 委托给扣子script-generate工作流

    Args:
        request: 剧本生成请求

    Returns:
        剧本生成结果
    """
    # 构建工作流请求参数
    payload = {
        "product_info": request.product_info,
        "style": request.style or request.video_style,
        "target_duration": request.target_duration,
        "selected_materials": request.selected_materials,
        "mode": request.mode,
        "template_id": request.template_id,
        "reference_video_id": request.reference_video_id,
        "additional_instructions": request.additional_instructions,
        "num_variants": request.num_variants,
        "aspect_ratio": request.aspect_ratio,
    }

    # 调用扣子工作流
    result = await call_workflow("script-generate", payload)

    # 解析工作流返回结果
    scenes_data = result.get("scenes", [])
    scenes = [Scene(**scene) for scene in scenes_data]

    # 计算总时长
    total_duration = sum(s.duration for s in scenes)

    return ScriptGenerateResponse(
        success=True,
        script_id=None,  # 后续可以保存到数据库后填充
        scenes=scenes,
        total_duration=total_duration,
        aspect_ratio=request.aspect_ratio,
        metadata={
            "workflow_result": result,
        },
    )
