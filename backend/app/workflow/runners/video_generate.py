"""本地视频生成运行器 — 直接调火山方舟 Seedance API"""
import asyncio
import random
import httpx
import os
import uuid
from PIL import Image, ImageDraw, ImageFont

VOLCANO_ARK_BASE = "https://ark.cn-beijing.volces.com/api/v3"
MODEL_EP = "ep-20260514120705-pqv86"  # Doubao-Seedance-1.5-pro
FONT_PATH = "/usr/share/fonts/truetype/wqy/msyh.ttc"  # 微软雅黑（fontconfig 已注册）



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
            ref_images = scene.get("reference_images", [])
            text_overlays = scene.get("text_overlays", [])
            has_text = len(text_overlays) > 0
            has_ref = len(ref_images) > 0

            # 只有文字没有图 → 创建一张纯文字图
            # 有图有文字 → 网格排列参考图 + 底部文字条
            # 有图无文字 → 网格排列参考图
            # 无图无文字 → 不传图片
            if has_ref or has_text:
                import httpx as _hx
                from PIL import Image as _PImg, ImageDraw as _PDraw, ImageFont as _PFont
                import io as _io

                # 下载所有参考图
                ref_imgs = []
                if has_ref:
                    async with _hx.AsyncClient(timeout=30) as _dl:
                        for ri in ref_images[:4]:  # 最多4张
                            url = ri.get("url", "")
                            if url:
                                try:
                                    resp = await _dl.get(url, timeout=10)
                                    if resp.status_code == 200:
                                        img = _PImg.open(_io.BytesIO(resp.content)).convert("RGB")
                                        ref_imgs.append(img)
                                except:
                                    pass

                n = len(ref_imgs)
                # 网格布局
                cell_w, cell_h = 360, 640  # 单格尺寸
                if n <= 1:
                    cols, rows = 1, 1
                    gw, gh = cell_w, cell_h
                elif n == 2:
                    cols, rows = 2, 1
                    gw, gh = cell_w * 2, cell_h
                elif n <= 4:
                    cols, rows = 2, 2
                    gw, gh = cell_w * 2, cell_h * 2

                # 文字条高度
                text_bar_h = 0
                if has_text:
                    text_bar_h = 30 + len(text_overlays) * 36

                canvas = _PImg.new("RGB", (gw, gh + text_bar_h), (30, 30, 30))
                # 贴参考图
                for idx2, img in enumerate(ref_imgs[:4]):
                    cx = (idx2 % cols) * cell_w
                    cy = (idx2 // cols) * cell_h
                    thumb = img.resize((cell_w, cell_h), _PImg.LANCZOS)
                    canvas.paste(thumb, (cx, cy))

                # 贴文字
                if has_text:
                    draw = _PDraw.Draw(canvas)
                    font = _PFont.truetype(FONT_PATH, 28)
                    y_pos = gh + 10
                    for to in text_overlays:
                        txt = to.get("text", "")
                        bbox = draw.textbbox((0, 0), txt, font=font)
                        tw = bbox[2] - bbox[0]
                        x_pos = (gw - tw) // 2
                        r_c, g_c, b_c = 255, 255, 255
                        for ox, oy in [(-1,-1),(-1,1),(1,-1),(1,1),(0,0)]:
                            draw.text((x_pos+ox, y_pos+oy), txt, font=font,
                                      fill=(r_c,g_c,b_c,255) if ox==0 and oy==0 else (0,0,0,200))
                        y_pos += 32

                # 保存合成图
                comp_name = f"grid_{session_id}_{scene_id}_{uuid.uuid4().hex[:8]}.jpg"
                comp_path = os.path.join(text_dir, comp_name)
                canvas.save(comp_path, "JPEG", quality=92)
                signed = generate_signed_url(
                    comp_path.replace("/app/uploads", "/uploads"),
                    expire_seconds=86400
                )
                content_items.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"http://114.117.242.17:3000{signed}",
                        "role": "reference_image",
                    }
                })
            # 3. 构建文字 prompt
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
                prompt += "\n【⏱ 时间轴执行规则】\n"
                prompt += "1. 人物说话不要视频一开始就开始说，开头留1-2秒缓冲\n"
                prompt += "2. 不要说到视频结尾，结尾至少留1秒静音过渡\n"
                prompt += "3. 两句台词之间留0.5-1秒间隔，不要连珠炮\n"
                prompt += "\n【重要·严禁事项】\n"
                prompt += "1. 画面中禁止出现剧本和素材以外的额外文字——只能包含剧本台词和素材图片中原有的文字\n"
                prompt += "2. 严禁出现剧本台词中没有的角色说话画面——角色只能说出剧本明确标注的台词，不能自己编词\n"
                prompt += "3. 旁白必须有声音输出（音频正常朗读），但画面中人物绝对不能出镜/对口型——旁白时段画面只展示场景和人物动作，无人说话\n"
                prompt += "4. 理解参考素材内容：素材图中有什么就生成什么，不要臆造素材中没有的物品/人物\n"
            prompt += "\n【空间布局要求】\n"
            prompt += "1. 参考图仅作为产品外观和风格参考，不要完全照搬构图\n"
            prompt += "2. 产品应位于画面中心或黄金分割点（偏左/偏右1/3处），占据画面1/4到1/2的面积\n"
            prompt += "3. 人物和产品之间的前后关系要明确：谁在前谁在后\n"
            prompt += "4. 避免画面过于空旷或过于拥挤，保持视觉平衡\n"
            prompt += "5. 如果有多个人物/物体，说明它们之间的相对位置（左右/前后/上下）\n"
            prompt += "6. 背景元素和前景元素要分层，营造景深感\n"
            prompt += "\n【剧本执行要求】\n"
            prompt += "1. **严格按照 visual_desc 的描述生成画面**，包括：镜头类型（特写/中景/全景）、主体位置、动作、光线\n"
            prompt += "2. 旁白配音必须严格按照时间轴朗读对应文本，不能省略或更改台词\n"
            prompt += "3. 角色说的话必须与 lines 中的 text 完全一致\n"
            prompt += "4. 每个时间段的画面必须匹配该时间段内的台词内容和语气\n"
            prompt += "5. 参考图只用于产品外观参考，场景构图必须按照 visual_desc 执行\n"
            prompt += "6. 确保画面中的人物动作与描述完全一致（如：微笑、拿起、指向等）"
            if text_overlays:
                prompt += "\n7. 已传入参考图（图中可能包含文字），请在视频中呈现同样的效果"
            content_items.append({"type": "text", "text": prompt})

            body = {"model": MODEL_EP, "content": content_items, "return_last_frame": False}
            import json as _json
            print(f"[seedance] scene {scene_id}: FULL_JSON({len(content_items)} items, ref_imgs={sum(1 for c in content_items if c.get("type")=="image_url")})")
            print(_json.dumps(body, indent=2, ensure_ascii=False)[:2000])
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
