"""
创作编排器 — 状态机驱动 7 步工作流
"""
import time
import json
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.states import TaskState, WORKFLOW_STEPS, TRANSITIONS, EDITABLE_STATES
from app.core.ws_manager import manager
from app.creation.models import VideoTask, TaskLog
from app.script.models import Script
from app.material import search as material_search_svc
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
        payload = await build_payload(db, task, workflow_name)
        result = await call_workflow(workflow_name, payload)

        # 保存结果
        task.status = f"{workflow_name.upper().replace('-', '_')}_DONE"
        await save_workflow_result(db, task, workflow_name, result)
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


async def build_payload(db: AsyncSession, task: VideoTask, workflow_name: str) -> dict:
    """
    根据工作流名称构造 payload
    C1: material-embed / query-generate
    C2: material-search - 从分镜提取关键词，匹配素材
    C3: video-generate - 分镜生视频
    C4: video-compose - 智能剪辑合成
    """
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
        # C2: 从 script 读取分镜，提取搜索关键词
        script = await _get_script(db, task)
        scenes = script.get("scenes", []) if script else []

        # 从每个分镜提取视觉描述和旁白作为搜索query
        search_queries = []
        for scene in scenes:
            desc = scene.get("visual_description", "") or scene.get("description", "")
            narration = scene.get("narration", "")
            if desc:
                search_queries.append(desc)
            if narration and len(narration) < 50:
                search_queries.append(narration)

        # 去重，取前5个最相关的query
        unique_queries = list(dict.fromkeys(search_queries))[:5]

        return {
            "product_queries": unique_queries,
            "general_queries": [],
        }

    elif workflow_name == "script-generate":
        # 把搜索到的素材传给脚本生成，让LLM知道有哪些素材可用
        selected_materials = getattr(task, "matched_materials", [])
        return {
            "product_info": task.product_info or {},
            "video_style": task.style or "电商带货",
            "target_duration": task.duration or 15,
            "selected_materials": selected_materials,
            "mode": "auto" if task.auto_mode else "manual",
        }

    elif workflow_name == "tts-generate":
        script = await _get_script(db, task)
        scenes = script.get("scenes", []) if script else []
        # 多语种TTS支持
        payload = {"scenes": scenes}
        if task.target_languages:
            payload["polyglot"] = True
            payload["target_languages"] = task.target_languages
        return payload

    elif workflow_name == "video-generate":
        # C3: 为每个分镜生成视频片段
        script = await _get_script(db, task)
        scenes = script.get("scenes", []) if script else []

        # 为每个分镜匹配素材（从任务缓存中取）
        matched_materials = getattr(task, "matched_materials", [])

        # 构建带素材的分镜数据
        scenes_with_materials = []
        for i, scene in enumerate(scenes):
            scene_data = {
                "scene_id": scene.get("scene_id", i + 1),
                "visual_description": scene.get("visual_description") or scene.get("description", ""),
                "narration": scene.get("narration", ""),
                "duration": scene.get("duration", 3),
            }
            # 如果有匹配的素材，加入
            if i < len(matched_materials):
                scene_data["material_url"] = matched_materials[i].get("image_url", "")
                scene_data["material_id"] = matched_materials[i].get("id", "")
            scenes_with_materials.append(scene_data)

        return {
            "task_id": str(task.id),
            "aspect_ratio": task.aspect_ratio or "9:16",
            "scenes": scenes_with_materials,
        }

    elif workflow_name == "video-compose":
        # C4: 合成最终视频，支持多语种
        script = await _get_script(db, task)
        scenes = script.get("scenes", []) if script else []

        # 从 video_urls 中读取每个分镜的视频片段
        # video_urls 格式: [{"scene_id": 1, "video_url": "...", "audio_url": "..."}]
        video_urls = task.video_urls or []

        # 确定使用的语言版本（默认用第一个目标语言，或zh-CN
        languages = task.target_languages or ["zh-CN"]
        selected_lang = languages[0]
        lang_tts = task.tts_results.get(selected_lang, {})
        scene_audios = lang_tts.get("scene_audios", [])

        # 构建完整分镜数据：视频 + 字幕 + 配音
        composed_scenes = []
        for i, scene in enumerate(scenes):
            scene_id = scene.get("scene_id", i + 1)
            scene_video = next((v for v in video_urls if v.get("scene_id") == scene_id), None)
            scene_audio = next((a for a in scene_audios if a.get("scene_id") == scene_id), None)
            composed_scenes.append({
                "scene_id": scene_id,
                "video_url": scene_video.get("video_url", "") if scene_video else "",
                "audio_url": scene_audio.get("audio_url", "") if scene_audio else (scene_video.get("audio_url", "") if scene_video else ""),
                "narration": scene.get("narration", ""),
                "subtitle": scene.get("subtitle") or scene.get("narration", ""),
                "duration": scene.get("duration", 3),
            })

        return {
            "task_id": str(task.id),
            "aspect_ratio": task.aspect_ratio or "9:16",
            "scenes": composed_scenes,
            "output_format": "mp4",
            "add_subtitles": True,
            "bgm_style": task.style or "电商",
            "language": selected_lang,  # 传给工作流用于字幕语言匹配
        }

    return {}


async def _get_script(db: AsyncSession, task: VideoTask) -> dict:
    """从数据库读取脚本内容"""
    if not task.script_id:
        return {}

    from sqlalchemy import select
    stmt = select(Script).where(Script.id == task.script_id)
    result = await db.execute(stmt)
    script = result.scalar_one_or_none()

    return script.content if script and script.content else {}


async def save_workflow_result(db: AsyncSession, task: VideoTask, workflow_name: str, result: dict):
    """
    将工作流结果保存到 task 上
    C2: material-search - 保存匹配到的素材
    C3: video-generate - 保存每个分镜生成的视频URL
    C4: video-compose - 保存最终合成视频URL
    """
    if workflow_name == "material-search":
        # C2: 保存搜索到的素材，供后续步骤使用
        materials = result.get("materials", []) or result.get("results", [])
        # 临时保存到 task 的缓存属性（也可以存到 video_urls JSONB 字段中）
        setattr(task, "matched_materials", materials[:10])  # 最多保存10个素材
        # 同时也存到 video_urls 中持久化
        task.video_urls = task.video_urls or []
        for m in materials[:10]:
            task.video_urls.append({
                "type": "material",
                "material_id": m.get("id"),
                "image_url": m.get("image_url"),
                "similarity": m.get("similarity"),
            })

    elif workflow_name == "script-generate":
        # C1: 创建脚本记录（A模块负责，这里只存到 task 缓存）
        scenes = result.get("scenes", [])
        setattr(task, "script_scenes", scenes)

    elif workflow_name == "tts-generate":
        # 保存配音结果，支持多语种
        if result.get("polyglot"):
            # 多语种模式: {zh-CN: {audio_url, scene_audios}, en-US: {...}}
            task.tts_results = result.get("languages", {})
            # 默认使用第一个语言作为主音频
            languages = task.target_languages or list(task.tts_results.keys())
            if languages:
                first_lang = languages[0]
                task.audio_url = task.tts_results.get(first_lang, {}).get("audio_url", "")
        else:
            # 单语种模式
            audio_results = result.get("audio_urls", []) or result.get("results", [])
            task.audio_url = audio_results[0].get("url") if audio_results else ""
            # 也存到tts_results里统一格式
            task.tts_results = {
                "zh-CN": {
                    "audio_url": task.audio_url,
                    "scene_audios": audio_results
                }
            }

    elif workflow_name == "video-generate":
        # C3: 保存每个分镜生成的视频片段
        video_results = result.get("video_urls", []) or result.get("results", [])
        if video_results:
            # 格式: [{"scene_id": 1, "video_url": "...", "audio_url": "..."}]
            task.video_urls = task.video_urls or []
            # 先移除旧的分镜视频
            task.video_urls = [v for v in task.video_urls if v.get("type") == "material"]
            # 添加新的分镜视频
            for v in video_results:
                task.video_urls.append({
                    "type": "scene_video",
                    "scene_id": v.get("scene_id"),
                    "video_url": v.get("video_url"),
                    "audio_url": v.get("audio_url"),
                })

    elif workflow_name == "video-compose":
        # C4: 保存最终合成视频
        task.output_url = result.get("output_url", "") or result.get("video_url", "")
        # 如果有多个画幅，都保存
        if result.get("output_urls"):
            for ratio, url in result["output_urls"].items():
                task.video_urls.append({
                    "type": "final_output",
                    "aspect_ratio": ratio,
                    "video_url": url,
                })
