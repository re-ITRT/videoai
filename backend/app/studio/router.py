"""工作流工作室 API — 基于 Session 文件夹存储"""
import json, os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.auth.models import User
from app.agent.models import ensure_session_dir

router = APIRouter(prefix="/api/v1/studio", tags=["studio"])

DEFAULT_STATE = {
    "products": [],
    "selected_product_id": None,
    "threshold": 30,
    "selected_material_ids": [],
    "collections": [],
    "selected_collection_id": None,
    "selected_template": "",
    "cached_materials": [],
    "last_script": None,
    "clip_collections": [],
    "selected_clip_collection_id": None,
    "final_videos": [],
}


def get_state_path(session_id: int) -> str:
    return os.path.join(ensure_session_dir(session_id)["root"], "workflow_state.json")


@router.get("/state/{session_id}")
async def get_workflow_state(session_id: int, user: User = Depends(get_current_user)):
    sp = get_state_path(session_id)
    if os.path.exists(sp):
        with open(sp, "r", encoding="utf-8") as f:
            return json.loads(f.read())
    return dict(DEFAULT_STATE)


@router.put("/state/{session_id}")
async def save_workflow_state(session_id: int, body: dict, user: User = Depends(get_current_user)):
    sp = get_state_path(session_id)
    with open(sp, "w", encoding="utf-8") as f:
        f.write(json.dumps(body, ensure_ascii=False, indent=2))
    return {"ok": True}


@router.post("/semantic-search")
async def semantic_search(body: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """产品介绍 → query-generate → material-search → 返回素材相似度列表"""
    from app.workers.workflow import call_workflow
    from app.material.search import search_materials_by_embeddings
    
    product_info = body.get("product_info", {})
    # 用低阈值搜索（0.1），让前端滑动实时筛选
    threshold = 0.1

    # 1. 调用 query-generate 生成关键词
    qg = await call_workflow("query-generate", {
        "product_info": {"product_id": 1, "name": product_info.get("title", ""), "description": product_info.get("content", "")},
        "video_style": "电商带货",
        "target_duration": 30,
    })
    product_queries = qg.get("product_queries", []) if isinstance(qg, dict) else []
    general_queries = qg.get("general_queries", []) if isinstance(qg, dict) else []

    # 2. 调用 material-search 生成向量
    ms = await call_workflow("material-search", {
        "product_queries": product_queries,
        "general_queries": general_queries,
    })
    embeddings = ms.get("product_embeddings", []) if isinstance(ms, dict) else []

    # 3. 用向量搜索 PG
    all_results = []
    seen = set()
    for emb in embeddings:
        vector = emb.get("embedding", [])
        if not vector:
            continue
        items = await search_materials_by_embeddings(db, str(user.id), vector, threshold)
        for item in items:
            item.pop("text_content", None)
            mid = item.get("id")
            if mid not in seen:
                seen.add(mid)
                all_results.append(item)

    all_results.sort(key=lambda r: r.get("similarity", 0), reverse=True)
    return {"materials": all_results, "total": len(all_results)}


@router.post("/generate-script")
async def studio_generate_script(body: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """直接生成剧本（不走LLM对话，直接调 runner 或 workflow）"""
    from app.workflow.runners.script_generate import run_script_generate
    from app.workflow.models import WorkflowConfig
    from sqlalchemy import select as _s
    import json, os

    product_content = body.get("product_content", "")
    template = body.get("template", "default")
    materials = body.get("materials", [])  # [{id, description, tags}]
    session_id = body.get("session_id", 0)

    params = {
        "product_info": {"product_id": 1, "name": product_content[:30], "description": product_content, "selling_points": []},
        "style": "电商带货",
        "duration": 30,
        "selected_materials": materials,
    }

    # 查工作流配置
    wf = await db.execute(_s(WorkflowConfig).where(WorkflowConfig.user_id == user.id, WorkflowConfig.workflow_name == "script-generate"))
    wf_cfg = wf.scalar_one_or_none()

    if wf_cfg and wf_cfg.enabled:
        cfg = json.loads(wf_cfg.config or "{}")
        if cfg.get("api_key") and cfg.get("base_url") and cfg.get("model"):
            result = await run_script_generate(api_key=cfg["api_key"], base_url=cfg["base_url"], model=cfg["model"], params=params, template=template)
            # 注入素材ID到每个场景（LLM可能忽略）
            result = _inject_materials(result, materials)
            _save_script(session_id, result)
            return result
    # fallback: 调 Coze workflow
    from app.workers.workflow import call_workflow
    result = await call_workflow("script-generate", params)
    result = _inject_materials(result, materials)
    _save_script(session_id, result)
    return result


def _inject_materials(script_data: dict, materials: list) -> dict:
    """强制将素材ID列表注入每个场景的 materials 字段（仅补充空场景）"""
    script_body = script_data.get("script", script_data)
    scenes = script_body.get("scenes", [])
    mid_list = [m.get("material_id") or m.get("id") for m in materials if m.get("material_id") or m.get("id")]
    if mid_list:
        for s in scenes:
            if not s.get("materials"):
                s["materials"] = mid_list  # fallback: 全部注入
    return script_data


def _save_script(session_id: int, script_data: dict):
    """保存剧本到 session 目录"""
    import json, os
    d = ensure_session_dir(session_id)
    spath = os.path.join(d["scripts"], f"script_{session_id}.json")
    with open(spath, "w", encoding="utf-8") as f:
        f.write(json.dumps(script_data, ensure_ascii=False, indent=2))


@router.post("/generate-video")
async def studio_generate_video(body: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """提交视频生成任务（异步，立即返回）"""
    from app.agent.models import ensure_session_dir, SessionFile, get_session_files as _gsf
    from app.workers.workflow import call_workflow
    from app.core.signer import generate_signed_url
    import json, os, asyncio

    session_id = body.get("session_id", 0)
    script_name = body.get("script_name", f"script_{session_id}")

    # 1. 读剧本文件
    sname = script_name or f"script_{session_id}"
    script_path = os.path.join(ensure_session_dir(session_id)["scripts"], f"{sname}.json")
    if not os.path.exists(script_path):
        raise HTTPException(404, f"剧本文件不存在: {script_name}")
    with open(script_path, "r", encoding="utf-8") as f:
        script_data = json.loads(f.read())
    script_body = script_data.get("script", script_data)
    scenes = script_body.get("scenes", [])
    title = script_body.get("title", "")
    style = script_body.get("style", "电商带货")
    if not scenes:
        raise HTTPException(400, "剧本没有场景")

    # 2. 获取素材图片（signed URL）— 优先用 scenes 中的 materials，否则用素材集合
    from sqlalchemy import select as _s
    from app.material.models import Material
    scene_mids = set()
    for s in scenes:
        for mid in s.get("materials", []):
            scene_mids.add(mid)
    # 如果 scenes 没指定素材，从工作流 state 的素材集合取
    if not scene_mids:
        state_path = os.path.join(ensure_session_dir(session_id)["root"], "workflow_state.json")
        if os.path.exists(state_path):
            with open(state_path, "r", encoding="utf-8") as f:
                st = json.loads(f.read())
            sel = st.get("selected_collection_id")
            coll = next((c for c in st.get("collections", []) if c.get("id") == sel), None)
            if coll:
                scene_mids = set(coll.get("material_ids", []))
    material_urls = {}
    if scene_mids:
        r = await db.execute(_s(Material).where(Material.id.in_(scene_mids)))
        for m in r.scalars().all():
            if m.image_url:
                signed = generate_signed_url(m.image_url, expire_seconds=86400)
                material_urls[m.id] = f"http://114.117.242.17:3000{signed}"

    # 3. 构建 reference_images
    for s in scenes:
        s["reference_images"] = [
            {"url": material_urls[mid], "role": "reference_image"}
            for mid in s.get("materials", []) if mid in material_urls
        ]
        if "lines" not in s:
            s["lines"] = []

    # 4. 提交任务
    aspect_ratio = body.get("aspect_ratio", "9:16")
    params = {
        "workflow_type": "generate",
        "script": {
            "title": title or script_body.get("title", f"视频_{session_id}"),
            "style": style or "电商带货",
            "aspect_ratio": aspect_ratio,
            "duration": sum(s.get("duration", 5) for s in scenes),
            "scenes": [{
                "scene_id": s.get("scene_id", i+1),
                "type": s.get("type", "scene"),
                "visual_desc": s.get("visual_desc", ""),
                "duration": s.get("duration", 5),
                "lines": s.get("lines", []),
                "reference_images": s.get("reference_images", []),
            } for i, s in enumerate(scenes)],
        },
    }

    # 检查本地工作流配置
    from app.workflow.models import WorkflowConfig
    wf = await db.execute(
        _s(WorkflowConfig).where(WorkflowConfig.user_id == user.id, WorkflowConfig.workflow_name == "video-generate")
    )
    wf_cfg = wf.scalar_one_or_none()
    local_api_key = None
    if wf_cfg and wf_cfg.enabled:
        cfg = json.loads(wf_cfg.config or "{}")
        local_api_key = cfg.get("api_key")

    if local_api_key:
        # 本地模式：调火山方舟 API
        from app.workflow.runners.video_generate import run_video_generate
        try:
            result = await run_video_generate(local_api_key, params)
        except Exception as e:
            raise HTTPException(502, f"本地视频生成失败: {str(e)}")
        save_mode = "local"
    else:
        # 兜底：调 Coze workflow
        try:
            result = await call_workflow("video-generate", params)
        except Exception as e:
            print(f"[generate-video] Coze ERROR: {e}")
            raise HTTPException(502, f"Coze workflow 返回错误: {str(e)}")
        save_mode = "coze"

    inner = result.get("result", result) if isinstance(result, dict) else result
    task_ids = inner.get("task_ids", []) if isinstance(inner, dict) else []
    print(f"[generate-video] task_ids count={len(task_ids)}")
    if not task_ids:
        raise HTTPException(500, "提交视频生成任务失败")

    # 5. 保存 task_ids（含模式标记）
    print(f"[generate-video] saving task_ids... session_id={session_id}, mode={save_mode}")
    sf = SessionFile(
        session_id=session_id, file_type="video_task",
        filename=f"tasks_{session_id}.json",
        file_url="",
        description=json.dumps({"mode": save_mode, "task_ids": task_ids, "api_key": local_api_key or ""}, ensure_ascii=False),
    )
    db.add(sf)
    await db.commit()
    print(f"[generate-video] saved, returning")
    return {"submitted": True, "task_ids": task_ids, "session_id": session_id}


@router.post("/poll-generate/{session_id}")
async def studio_poll_generate(session_id: int, db: AsyncSession = Depends(get_db)):
    """轮询视频生成状态（无需登录）"""
    from app.agent.models import SessionFile, get_session_files as _gsf
    from app.workers.workflow import call_workflow
    import json

    files = await _gsf(db, session_id)
    tasks = [f for f in files if f.file_type == "video_task"]
    if not tasks:
        return {"status": "no_task", "clips": [], "total": 0}

    latest = tasks[0]  # 最新的 task（created_at DESC）
    raw = json.loads(latest.description)
    # 兼容新旧格式: 旧格式直接是 list，新格式是 {"mode":..., "task_ids":..., "api_key":...}
    if isinstance(raw, dict) and "task_ids" in raw:
        task_ids = raw["task_ids"]
        mode = raw.get("mode", "coze")
        api_key = raw.get("api_key", "")
    else:
        task_ids = raw
        mode = "coze"
        api_key = ""

    if mode == "local" and api_key:
        from app.workflow.runners.video_generate import query_video_status
        try:
            qr = await query_video_status(api_key, task_ids)
        except Exception:
            return {"status": "error", "detail": "Local query failed"}
        qr_inner = qr
    else:
        try:
            qr = await call_workflow("video-generate", {
                "workflow_type": "query",
                "task_ids": task_ids,
            })
        except Exception:
            return {"status": "error", "detail": "Coze query failed"}
        qr_inner = qr.get("result", qr) if isinstance(qr, dict) else qr
    if not isinstance(qr_inner, dict):
        return {"status": "unknown", "clips": []}

    if qr_inner.get("status") == "completed":
        clips = qr_inner.get("video_clips", [])
        saved_ids = []
        for clip in clips:
            vu = clip.get("video_url", "")
            if vu:
                sf = SessionFile(
                    session_id=session_id, file_type="video_clip",
                    filename=f"clip_{session_id}_scene{clip.get('scene_id', '')}.mp4",
                    file_url=vu,
                    description=f"场景 {clip.get('scene_id', '')} 视频片段",
                )
                db.add(sf)
                await db.flush()
                saved_ids.append(sf.id)
        await db.commit()
        # 只返回本次新保存的 clips
        fresh = await _gsf(db, session_id)
        all_clips = {f.id: {"id": f.id, "scene_id": (f.description or "").replace("场景 ", "").replace(" 视频片段", ""), "url": f.file_url}
                     for f in fresh if f.file_type == "video_clip"}
        new_clips = [all_clips[cid] for cid in saved_ids if cid in all_clips]
        return {"status": "completed", "clips": new_clips, "saved": len(new_clips), "total": len(all_clips)}
    elif qr_inner.get("status") == "running":
        return {"status": "running", "clips": []}
    else:
        return {"status": "unknown", "detail": str(qr_inner)}


@router.post("/compose-video")
async def studio_compose_video(body: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """合成视频：调 Coze 工作流拼接 clip（不传台词，不做TTS）"""
    from app.agent.models import SessionFile, get_session_files as _gsf
    from app.workers.workflow import call_workflow
    import json

    session_id = body.get("session_id", 0)
    clip_ids = body.get("clip_ids")

    files = await _gsf(db, session_id)
    clips = [f for f in files if f.file_type == "video_clip"]
    if clip_ids:
        clips = [f for f in clips if f.id in clip_ids]
    if not clips:
        raise HTTPException(400, "没有可合成的视频片段")

    # 按场景排序
    def _sid(vf):
        s = (vf.description or "").replace("场景 ", "").replace(" 视频片段", "")
        return int(s) if s.isdigit() else 0
    clips.sort(key=_sid)

    scenes = [{"scene_id": _sid(vf), "video_url": vf.file_url, "duration": 5, "lines": []} for vf in clips]
    payload = {"scenes": scenes}

    result = await call_workflow("video-compose", payload)

    output_url = ""
    if isinstance(result, dict):
        inner = result.get("result", result)
        if isinstance(inner, dict):
            output_url = inner.get("output_video_url", "") or inner.get("video_url", "")
        output_url = output_url or result.get("output_video_url", "") or result.get("video_url", "")

    if output_url:
        sf = SessionFile(
            session_id=session_id, file_type="final_video",
            filename=f"final_{session_id}.mp4",
            file_url=output_url,
            description="Coze 合成视频",
        )
        db.add(sf)
        await db.commit()
        return {"composed": True, "videos": [{"id": sf.id, "url": output_url}]}

    return {"composed": False, "error": "合成失败", "detail": str(result)}


@router.get("/clips/{session_id}")
async def get_session_clips(session_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """获取 session 的视频片段"""
    from app.agent.models import SessionFile, get_session_files as _gsf
    files = await _gsf(db, session_id)
    clips = [{"id": f.id, "scene_id": (f.description or "").replace("场景 ", "").replace(" 视频片段", ""), "url": f.file_url} for f in files if f.file_type == "video_clip"]
    final = [{"id": f.id, "url": f.file_url} for f in files if f.file_type == "final_video"]
    return {"clips": clips, "final_videos": final}


@router.post("/delete-clip")
async def studio_delete_clip(body: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """删除指定 SessionFile（视频片段或最终视频）"""
    from app.agent.models import SessionFile
    from sqlalchemy import select as _s
    clip_id = body.get("clip_id")
    if not clip_id:
        raise HTTPException(400, "clip_id required")
    r = await db.execute(_s(SessionFile).where(SessionFile.id == clip_id))
    sf = r.scalar_one_or_none()
    if not sf:
        return {"ok": False, "error": "not found"}
    await db.delete(sf)
    await db.commit()
    return {"ok": True}


@router.post("/materials/search")
async def search_studio_materials(body: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """搜索素材（带阈值和标签）"""
    from sqlalchemy import select as _s, text as _t
    from app.material.models import Material
    threshold = body.get("threshold", 30) / 100.0
    tags = body.get("tags", [])
    query = _s(Material).where(Material.user_id == str(user.id))
    if tags:
        for tag in tags:
            query = query.where(Material.tags.contains(_t(f'"{tag}"')))
    r = await db.execute(query.order_by(Material.id.desc()))
    items = [{"id": m.id, "image_url": m.image_url, "tags": m.tags, "similarity": 1.0} for m in r.scalars().all()]
    return {"materials": items, "total": len(items)}


# ── AI 剧本编辑 ──────────────────────────

AI_EDIT_TOOLS = [
    {"type": "function", "function": {
        "name": "read_script",
        "description": "读取当前剧本内容",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "change_text",
        "description": "修改剧本中的台词文本。传入旧文本和新文本，系统自动在剧本中查找替换。",
        "parameters": {"type": "object", "properties": {
            "old_text": {"type": "string", "description": "当前台词文本（完整匹配）"},
            "new_text": {"type": "string", "description": "替换后的新文本"},
        }, "required": ["old_text", "new_text"]},
    }},
    {"type": "function", "function": {
        "name": "change_duration",
        "description": "修改指定场景的时长",
        "parameters": {"type": "object", "properties": {
            "scene_id": {"type": "string", "description": "场景ID（数字）"},
            "new_duration": {"type": "string", "description": "新时长秒数，限4/8/12"},
        }, "required": ["scene_id", "new_duration"]},
    }},
    {"type": "function", "function": {
        "name": "change_visual_desc",
        "description": "修改指定场景的视觉描述",
        "parameters": {"type": "object", "properties": {
            "scene_id": {"type": "string", "description": "场景ID（数字）"},
            "new_desc": {"type": "string", "description": "新的视觉描述文本"},
        }, "required": ["scene_id", "new_desc"]},
    }},
]

AI_EDIT_SYSTEM = "你是短视频剧本编辑助手。根据用户需求修改剧本。\n\n规则：\n1. 先用 read_script 读取剧本\n2. 使用 change_text / change_duration / change_visual_desc 工具进行修改\n3. 每次修改后告知用户改了哪里"


@router.post("/ai-edit")
async def studio_ai_edit(body: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """AI 剧本编辑对话"""
    from app.ai.models import UserAIConfig
    from sqlalchemy import select as _s
    import json, httpx

    session_id = body.get("session_id", 0)
    script_name = body.get("script_name", f"script_{session_id}")
    messages = body.get("messages", [])
    template = body.get("template", "default")

    # 获取模板规则（附加到 system prompt）
    from app.workflow.runners.script_generate import _read_prompt
    extra_rules = ""
    for fname in ["rules.md", "output_format.md"]:
        p = os.path.join(os.path.dirname(__file__), "..", "workflow", "prompts", fname)
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                extra_rules += f"\n\n--- {fname} ---\n" + f.read()
    template_system = _read_prompt(template, "system.md") if template else ""
    full_system = AI_EDIT_SYSTEM
    if template_system:
        full_system += f"\n\n当前模板《{template}》的角色定义：\n{template_system}"
    full_system += f"\n\n当前剧本需遵守的规则：{extra_rules}"

    # 获取用户 AI 配置
    cfg = await db.execute(_s(UserAIConfig).where(UserAIConfig.user_id == user.id))
    cfg = cfg.scalar_one_or_none()
    if not cfg or not cfg.api_key:
        return {"error": "请先在个人中心配置 AI API Key"}

    api_key = cfg.api_key
    base_url = cfg.base_url or "https://api.deepseek.com/v1"
    model = cfg.model or "deepseek-v4-flash"

    # 构建消息列表
    msgs = [{"role": "system", "content": full_system}] + messages

    async def call_llm(_msgs, _tools=None):
        payload = {"model": model, "messages": _msgs, "temperature": 0.3}
        if _tools:
            payload["tools"] = _tools
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            if r.status_code != 200:
                print(f"[ai-edit] LLM {r.status_code}: {r.text[:500]}")
            r.raise_for_status()
            return r.json()

    # 工具循环（最多 5 轮）
    for _ in range(5):
        data = await call_llm(msgs, AI_EDIT_TOOLS)
        choice = data["choices"][0]
        msg = choice["message"]
        msgs.append({"role": "assistant", "content": msg.get("content", "")})
        if msg.get("tool_calls"):
            msgs[-1]["tool_calls"] = msg["tool_calls"]

        if not msg.get("tool_calls"):
            break

        for tc in msg["tool_calls"]:
            fn = tc["function"]
            name = fn["name"]
            try:
                args = json.loads(fn.get("arguments", "{}"))
                print(f"[ai-edit] tool={name} args={json.dumps(args, ensure_ascii=False)[:200]}")
                args.setdefault("script_name", script_name)
                if name in ("change_text", "change_duration", "change_visual_desc"):
                    # 直接修改文件，不走 execute_tool
                    from app.agent.models import ensure_session_dir
                    sp = os.path.join(ensure_session_dir(session_id)["scripts"], f"{script_name}.json")
                    if not os.path.exists(sp):
                        result = {"error": "剧本文件不存在"}
                    else:
                        with open(sp, "r", encoding="utf-8") as f:
                            sd = json.loads(f.read())
                        sb = sd.get("script", sd)
                        if name == "change_text":
                            old = args.get("old_text", "")
                            new_t = args.get("new_text", "")
                            changed = False
                            for sc in sb.get("scenes", []):
                                for ln in sc.get("lines", []):
                                    if old and ln.get("text") == old:
                                        ln["text"] = new_t
                                        changed = True
                            if changed:
                                with open(sp, "w", encoding="utf-8") as f:
                                    json.dump(sd, f, ensure_ascii=False, indent=2)
                                result = {"ok": True, "msg": f"已将「{old}」改为「{new_t}」"}
                            else:
                                result = {"error": f"未找到文本「{old}」"}
                        elif name == "change_duration":
                            sid = int(args.get("scene_id", 0))
                            nd = int(args.get("new_duration", 0))
                            for sc in sb.get("scenes", []):
                                if sc.get("scene_id") == sid:
                                    sc["duration"] = nd
                                    with open(sp, "w", encoding="utf-8") as f:
                                        json.dump(sd, f, ensure_ascii=False, indent=2)
                                    result = {"ok": True, "msg": f"场景{sid}时长改为{nd}秒"}
                                    break
                            else:
                                result = {"error": f"未找到场景{sid}"}
                        elif name == "change_visual_desc":
                            sid = int(args.get("scene_id", 0))
                            nd = args.get("new_desc", "")
                            for sc in sb.get("scenes", []):
                                if sc.get("scene_id") == sid:
                                    sc["visual_desc"] = nd
                                    with open(sp, "w", encoding="utf-8") as f:
                                        json.dump(sd, f, ensure_ascii=False, indent=2)
                                    result = {"ok": True, "msg": f"场景{sid}视觉描述已更新"}
                                    break
                            else:
                                result = {"error": f"未找到场景{sid}"}
                else:
                    from app.agent.router import execute_tool
                    result_str = await execute_tool(name, args, db, session_id, user)
                    result = json.loads(result_str)
            except Exception as e:
                result = {"error": str(e)}
            msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(result, ensure_ascii=False)})

    # 获取最后 assistant 回复
    last_assistant = ""
    updated_script = None
    for m in reversed(msgs):
        if m["role"] == "assistant" and m.get("content"):
            last_assistant = m["content"]
            break

    # 检查是否有编辑工具被调用
    for m in msgs:
        if m["role"] == "tool":
            try:
                content = json.loads(m["content"])
                if content.get("ok"):
                    # 重新读取最新剧本
                    spath = os.path.join(ensure_session_dir(session_id)["scripts"], f"{script_name}.json")
                    if os.path.exists(spath):
                        with open(spath, "r", encoding="utf-8") as f:
                            updated_script = json.loads(f.read())
            except Exception:
                pass

    return {"reply": last_assistant, "script": updated_script, "messages": msgs[1:]}  # 不包括 system
