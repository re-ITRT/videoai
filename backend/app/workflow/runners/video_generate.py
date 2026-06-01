"""本地视频生成运行器 — 直接调火山方舟 Seedance API"""
import asyncio
import random
import httpx

VOLCANO_ARK_BASE = "https://ark.cn-beijing.volces.com/api/v3"
MODEL_EP = "ep-20260514120705-pqv86"  # Doubao-Seedance-1.5-pro


async def run_video_generate(api_key: str, params: dict) -> dict:
    """
    提交视频生成任务（逐个场景串行提交）
    params: {script: {title, style, aspect_ratio, scenes: [...]}}
    返回: {task_ids: [{scene_id, task_id}]}
    """
    script = params.get("script", {})
    scenes = script.get("scenes", [])
    aspect_ratio = script.get("aspect_ratio", "9:16")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    task_ids = []
    async with httpx.AsyncClient(timeout=30) as client:
        for i, scene in enumerate(scenes):
            scene_id = scene.get("scene_id", i + 1)

            # 构建 content: 参考图 + 文本
            content_items = []
            for ref_img in scene.get("reference_images", []):
                content_items.append({
                    "type": "image_url",
                    "image_url": {
                        "url": ref_img.get("url"),
                        "role": ref_img.get("role", "reference_image"),
                    }
                })
            visual_desc = scene.get("visual_desc", "")
            lines = scene.get("lines", [])
            prompt = visual_desc
            if lines:
                prompt += "\n\n【台词】" + "; ".join(
                    f"{l.get('speaker', '')}: {l.get('text', '')}" for l in lines
                )
            content_items.append({"type": "text", "text": prompt})

            body = {"model": MODEL_EP, "content": content_items, "return_last_frame": False}
            if aspect_ratio:
                body["ratio"] = aspect_ratio

            # 提交 + 429 重试
            task_id = None
            for retry in range(3):
                try:
                    resp = await client.post(
                        f"{VOLCANO_ARK_BASE}/contents/generations/tasks",
                        json=body, headers=headers,
                    )
                    if resp.status_code == 429:
                        wait = (retry + 1) * 10 + random.randint(0, 5)
                        await asyncio.sleep(wait)
                        continue
                    resp.raise_for_status()
                    result = resp.json()
                    task_id = result.get("id")
                    break
                except Exception:
                    if retry < 2:
                        await asyncio.sleep((retry + 1) * 10)

            if task_id:
                task_ids.append({"scene_id": scene_id, "task_id": task_id})

            # 场景间延迟 2-3 秒
            if i < len(scenes) - 1:
                await asyncio.sleep(2 + random.randint(0, 2))

    return {"task_ids": task_ids}


async def query_video_status(api_key: str, task_ids: list) -> dict:
    """
    查询视频生成状态
    task_ids: [{scene_id, task_id}]
    返回: {status: "completed"/"running", video_clips: [...]}
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    clips = []
    all_done = True

    async with httpx.AsyncClient(timeout=30) as client:
        for item in task_ids:
            scene_id = item.get("scene_id")
            task_id = item.get("task_id")
            try:
                resp = await client.get(
                    f"{VOLCANO_ARK_BASE}/contents/generations/tasks/{task_id}",
                    headers=headers,
                )
                resp.raise_for_status()
                result = resp.json()

                status = result.get("status")
                if status == "succeeded":
                    video_url = result.get("content", {}).get("video_url", "")
                    if video_url:
                        clips.append({
                            "scene_id": scene_id,
                            "video_url": video_url,
                            "duration": float(result.get("duration", 5.0)),
                        })
                elif status in ("queued", "running"):
                    all_done = False
                # failed/cancelled: skip
            except Exception:
                all_done = False

    return {
        "status": "completed" if all_done else "running",
        "video_clips": clips,
    }
