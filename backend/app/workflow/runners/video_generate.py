"""本地视频生成运行器 — 直接调火山方舟 Seedance API"""
import asyncio
import random
import httpx
import os
import uuid
from PIL import Image, ImageDraw, ImageFont

VOLCANO_ARK_BASE = "https://ark.cn-beijing.volces.com/api/v3"
MODEL_EP = "ep-20260514120705-pqv86"  # Doubao-Seedance-1.5-pro
FONT_PATH = "/usr/share/fonts/truetype/wqy/msyh.ttc"  # 微软雅黑


def render_text_overlay(overlay: dict, out_path: str, img_w: int = 720, img_h: int = 1280):
    """将文字渲染到透明背景 PNG 上（白色文字+黑色描边）"""
    text = overlay.get("text", "")
    x_pct = overlay.get("x", 50)
    y_pct = overlay.get("y", 50)
    font_size = overlay.get("font_size", 36)
    color = overlay.get("color", "#FFFFFF")
    align = overlay.get("align", "center")
    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    cx, cy = int(img_w * x_pct / 100), int(img_h * y_pct / 100)
    x = cx - tw // 2 if align == "center" else cx - tw if align == "right" else cx
    y = cy - th // 2
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    # 黑色描边
    for ox, oy in [(-2,-2),(-2,2),(2,-2),(2,2),(-1,-1),(-1,1),(1,-1),(1,1),(0,0)]:
        draw.text((x+ox, y+oy), text, font=font,
                  fill=(r,g,b,255) if ox==0 and oy==0 else (0,0,0,200))
    img.save(out_path, "PNG")


async def run_video_generate(api_key: str, params: dict) -> dict:
    """
    提交视频生成任务（逐个场景串行提交）
    params: {script: {title, style, aspect_ratio, scenes: [...]}, session_id: int}
    返回: {task_ids: [{scene_id, task_id}]}
    """
    from app.core.signer import generate_signed_url
    script = params.get("script", {})
    scenes = script.get("scenes", [])
    aspect_ratio = script.get("aspect_ratio", "9:16")
    session_id = params.get("session_id", 0)
    text_dir = os.path.join("/app/uploads/agent_sessions", str(session_id), "text_overlays")
    os.makedirs(text_dir, exist_ok=True)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    task_ids = []
    async with httpx.AsyncClient(timeout=30) as client:
        for i, scene in enumerate(scenes):
            scene_id = scene.get("scene_id", i + 1)
            content_items = []

            # 1. 原有参考图（素材图片）
            for ref_img in scene.get("reference_images", []):
                content_items.append({
                    "type": "image_url",
                    "role": "reference_image",
                    "image_url": {
                        "url": ref_img.get("url"),
                    }
                })

            # 2. 渲染文字 overlay 为透明 PNG，当参考图传给 Seedance
            text_overlays = scene.get("text_overlays", [])
            for to_idx, to in enumerate(text_overlays):
                out_name = f"text_{session_id}_{scene_id}_{to_idx}_{uuid.uuid4().hex[:8]}.png"
                out_path = os.path.join(text_dir, out_name)
                try:
                    render_text_overlay(to, out_path)
                    signed = generate_signed_url(
                        out_path.replace("/app/uploads", "/uploads"),
                        expire_seconds=86400
                    )
                    url = f"http://114.117.242.17:3000{signed}"
                    content_items.append({
                        "type": "image_url",
                        "role": "reference_image",
                        "image_url": {
                            "url": url,
                        }
                    })
                except Exception as e:
                    print(f"[text_overlay] render failed: {e}")

            visual_desc = scene.get("visual_desc", "")
            lines = scene.get("lines", [])
            prompt = visual_desc
            if lines:
                prompt += "\n\n【画面时间轴·严格按此顺序】\n"
                for l in lines:
                    s = l.get('start_sec', 0)
                    e = l.get('end_sec', 5)
                    speaker = l.get('speaker', '')
                    text = l.get('text', '')
                    tone = l.get('tone', '中性')
                    if speaker == '旁白':
                        prompt += f"{s}-{e}秒: 旁白画外音（音频正常朗读台词，画面中人物不出镜不张嘴）「{text}」(语气: {tone})\n"
                    else:
                        prompt += f"{s}-{e}秒: 画面中的{speaker}说出「{text}」(语气: {tone})\n"
                prompt += "\n【区分说明】旁白是画外音（有声音但画面无人出镜说话），其他角色须在画面中出现并说出台词。以上顺序不能颠倒。\n"
            # 空间关系
            prompt += "\n【空间布局要求】\n"
            prompt += "1. 参考图仅作为产品外观和风格参考，不要完全照搬构图\n"
            prompt += "2. 产品应位于画面中心或黄金分割点（偏左/偏右1/3处），占据画面1/4到1/2的面积\n"
            prompt += "3. 人物和产品之间的前后关系要明确：谁在前谁在后\n"
            prompt += "4. 避免画面过于空旷或过于拥挤，保持视觉平衡\n"
            prompt += "5. 如果有多个人物/物体，说明它们之间的相对位置（左右/前后/上下）\n"
            prompt += "6. 背景元素和前景元素要分层，营造景深感\n"
            # 剧本执行
            prompt += "\n【剧本执行要求】\n"
            prompt += "1. **严格按照 visual_desc 的描述生成画面**，包括：镜头类型（特写/中景/全景）、主体位置、动作、光线\n"
            prompt += "2. 旁白配音必须严格按照时间轴朗读对应文本，不能省略或更改台词\n"
            prompt += "3. 角色说的话必须与 lines 中的 text 完全一致\n"
            prompt += "4. 每个时间段的画面必须匹配该时间段内的台词内容和语气\n"
            prompt += "5. 参考图只用于产品外观参考，场景构图必须按照 visual_desc 执行\n"
            prompt += "6. 确保画面中的人物动作与描述完全一致（如：微笑、拿起、指向等）"
            content_items.append({"type": "text", "text": prompt})

# image debug removed
            body = {"model": MODEL_EP, "content": content_items, "return_last_frame": False}
            if aspect_ratio:
                body["ratio"] = aspect_ratio
            dur = scene.get("duration")
            if dur in (4, 8, 12):
                body["duration"] = dur

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
                    if resp.status_code != 200:
                        print(f"[seedance] ERROR {resp.status_code}: {resp.text[:500]}")
                    resp.raise_for_status()
                    result = resp.json()
                    task_id = result.get("id")
                    break
                except Exception:
                    if retry < 2:
                        await asyncio.sleep((retry + 1) * 10)

            if task_id:
                task_ids.append({"scene_id": scene_id, "task_id": task_id})

            if i < len(scenes) - 1:
                await asyncio.sleep(2 + random.randint(0, 2))

    return {"task_ids": task_ids}


async def query_video_status(api_key: str, task_ids: list) -> dict:
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
            except Exception:
                all_done = False
    return {"status": "completed" if all_done else "running", "video_clips": clips}
