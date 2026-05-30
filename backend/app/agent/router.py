"""AI Agent 路由 — Session 管理 + 聊天 + 工具调用"""
import asyncio
import json
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func
from app.core.database import get_db, async_session
from app.core.deps import get_current_user
from app.auth.models import User
from app.core.logging import get_logger
from app.agent.models import (
    AgentSession, AgentMessage, SessionFile,
    SessionCreate, SessionResponse, MessageResponse, SessionFileResponse,
    create_session, list_sessions, delete_session, get_session_messages, get_session_files,
)
from app.workers.workflow import call_workflow

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


# ── Session CRUD ───────────────────────────

logger = get_logger("agent")

# ── Session CRUD ───────────────────────────

@router.get("/sessions", response_model=list[SessionResponse])
async def list_agent_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出用户的对话 Session"""
    sessions = await list_sessions(db, current_user.id)
    result = []
    for s in sessions:
        cnt = await db.execute(
            select(sa_func.count()).select_from(AgentMessage).where(AgentMessage.session_id == s.id)
        )
        result.append(SessionResponse(
            id=s.id, title=s.title or "新对话",
            message_count=cnt.scalar() or 0,
            created_at=s.created_at,
        ))
    return result


@router.post("/sessions", response_model=SessionResponse)
async def create_agent_session(
    req: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建新对话 Session"""
    sess = await create_session(db, current_user.id, req.title)
    return SessionResponse(id=sess.id, title=sess.title, message_count=0, created_at=sess.created_at)


@router.delete("/sessions/{session_id}")
async def delete_agent_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除对话 Session（含消息 + 文件）"""
    ok = await delete_session(db, session_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True}


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取 Session 的消息历史"""
    msgs = await get_session_messages(db, session_id)
    return [
        MessageResponse(
            id=m.id, role=m.role, content=m.content,
            tool_calls=json.loads(m.tool_calls) if m.tool_calls else None,
            created_at=m.created_at,
        )
        for m in msgs
    ]


@router.get("/sessions/{session_id}/files", response_model=list[SessionFileResponse])
async def get_session_files_endpoint(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取 Session 生成的文件"""
    files = await get_session_files(db, session_id)
    return [SessionFileResponse.model_validate(f) for f in files]


# ── 工具定义 ───────────────────────────────

TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "query_generate",
            "description": "【步骤1】根据产品信息和视频风格，生成用于素材搜索的关键词",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_info": {
                        "type": "object",
                        "description": "产品信息，必须包含 product_id、name、description",
                        "properties": {
                            "product_id": {"type": "integer", "description": "产品ID"},
                            "name": {"type": "string", "description": "产品名称"},
                            "description": {"type": "string", "description": "产品描述"},
                            "category": {"type": "string", "description": "产品类目"},
                            "selling_points": {"type": "array", "items": {"type": "string"}, "description": "卖点列表"},
                        },
                        "required": ["product_id", "name"],
                    },
                    "video_style": {"type": "string", "description": "视频风格，如：电商带货、产品展示"},
                    "target_duration": {"type": "integer", "description": "目标时长（秒）"},
                },
                "required": ["product_info"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "material_search",
            "description": "【步骤2】用关键词搜索已有素材，从本地素材库中检索匹配的图片/视频素材",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "产品相关搜索词，来自 query_generate 的输出",
                    },
                    "general_queries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "category": {"type": "string", "description": "类别：场景/氛围/特效/音效"},
                                "queries": {"type": "array", "items": {"type": "string"}, "description": "搜索词数组"},
                            },
                        },
                        "description": "通用素材搜索词",
                    },
                    "threshold": {"type": "number", "description": "相似度阈值 0-1，默认0.6"},
                },
                "required": ["product_queries", "general_queries"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_script",
            "description": "【步骤3】生成带货视频的结构化剧本",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_info": {
                        "type": "object",
                        "description": "产品信息",
                        "properties": {
                            "product_id": {"type": "integer"},
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "category": {"type": "string"},
                            "selling_points": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["product_id", "name"],
                    },
                    "selected_materials": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "material_id": {"type": "integer"},
                                "image_url": {"type": "string"},
                                "description": {"type": "string"},
                            },
                        },
                        "description": "从 material_search 选出的素材",
                    },
                    "style": {"type": "string", "description": "视频风格"},
                    "target_duration": {"type": "integer", "description": "目标时长（秒）"},
                },
                "required": ["product_info"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_video",
            "description": "【步骤4】根据剧本分镜描述生成 AI 视频片段，文件存入 session 的 video_clips/ 目录",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "剧本标题"},
                    "style": {"type": "string", "description": "视频风格"},
                    "scenes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "scene_id": {"type": "integer"},
                                "duration": {"type": "integer", "description": "片段时长（秒）"},
                                "visual_desc": {"type": "string", "description": "画面描述"},
                                "lines": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "speaker": {"type": "string", "description": "说话人（旁白/角色名）"},
                                            "text": {"type": "string", "description": "台词内容"},
                                            "tone": {"type": "string", "description": "语气语调"},
                                            "start_sec": {"type": "number", "description": "在该场景中开始秒数"},
                                            "end_sec": {"type": "number", "description": "在该场景中结束秒数"},
                                        },
                                    },
                                    "description": "台词时间轴列表",
                                },
                                "materials": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "用到的素材ID列表",
                                },
                            },
                        },
                        "description": "分镜列表（请从剧本中的 scenes 原样传入，含 lines 和 materials）",
                    },
                    "aspect_ratio": {"type": "string", "description": "画幅比例 9:16 或 16:9", "default": "9:16"},
                },
                "required": ["scenes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compose_video",
            "description": "【步骤6】将视频片段 + 音频 + 字幕合成为最终带货视频，文件存入 session 的 final_videos/ 目录",
            "parameters": {
                "type": "object",
                "properties": {
                    "script_text": {"type": "string", "description": "旁白文字（用于字幕）"},
                    "aspect_ratio": {"type": "string", "description": "画幅比例 9:16 或 16:9", "default": "9:16"},
                },
                "required": ["script_text"],
            },
        },
    },
]


# ── 助手系统提示 ──────────────────────────

SYSTEM_PROMPT = """你是 Video-AI 平台的 AI 助手，帮助用户生成电商带货视频。

## 视频生成流程（严格按顺序执行）

### 步骤 1 — 关键词生成 (query_generate)
用户提供产品信息后，先用 query_generate 生成搜索关键词。
输出包含 product_queries（产品词）和 general_queries（场景/氛围/特效/音效词）。

### 步骤 2 — 素材搜索 (material_search)
用关键词搜索已有素材库，将结果呈现给用户确认。
如果素材不够，可以调整阈值重新搜索。

### 步骤 3 — 剧本生成 (generate_script)
基于产品信息和选定的素材，生成结构化剧本（含台词时间轴 lines 和素材引用 materials）。

### 步骤 4 — 视频生成 (generate_video)
根据剧本分镜生成 AI 视频片段，视频生成内部自动处理语音和音效。文件存入 session 的 video_clips/ 目录。
传入的 scenes 应包含剧本中的 lines（台词时间轴）和 materials（素材ID列表），以便视频生成参考。

### 步骤 5 — 视频合成 (compose_video)
将视频片段合成为最终视频，存入 final_videos/ 目录。

## 核心规则
- 必须按 1→2→3→4→5 顺序执行，不能跳步
- 每步完成后向用户说明结果
- 工具执行结果会通过 role=tool 消息返回，自动记录到数据库
- 用户可以在中间步骤调整参数（如换关键词、选不同素材）
- 所有生成的文件都会记录在 SessionFile 表中，前端文件抽屉可查看
- 如果用户提供的信息不足（如缺少产品信息），主动询问"""


# ── 工具执行函数 ──────────────────────────

async def execute_tool(tool_name: str, args: dict, db: AsyncSession, session_id: int, user: User) -> str:
    """执行 AI 调用的工具，返回结果文本"""
    try:
        if tool_name == "query_generate":
            product_info = args.get("product_info", {})
            payload = {
                "product_info": product_info,
                "video_style": args.get("video_style", "电商带货"),
                "target_duration": args.get("target_duration", 15),
            }
            result = await call_workflow("query-generate", payload)
            return json.dumps(result, ensure_ascii=False, indent=2)

        elif tool_name == "material_search":
            product_queries = args.get("product_queries", [])
            general_queries = args.get("general_queries", [])
            threshold = args.get("threshold", 0.6)
            # 调用 material-search 工作流生成向量
            msearch_payload = {
                "product_queries": product_queries,
                "general_queries": general_queries,
            }
            embedding_result = await call_workflow("material-search", msearch_payload)
            # 用返回的向量搜索本地 PG
            from app.material.search import search_materials_by_embeddings
            all_results = []
            for pe in embedding_result.get("product_embeddings", []):
                query = pe.get("query", "")
                emb = pe.get("embedding", [])
                if emb:
                    items = await search_materials_by_embeddings(db, str(user.id), emb, threshold)
                    for item in items:
                        item["source_query"] = query
                        all_results.append(item)
            # 去重
            seen = set()
            unique = []
            for item in all_results:
                mid = item.get("id")
                if mid not in seen:
                    seen.add(mid)
                    unique.append(item)
            return json.dumps({"total": len(unique), "materials": unique[:20]}, ensure_ascii=False, indent=2)

        elif tool_name == "generate_script":
            payload = {
                "product_info": args.get("product_info", {}),
                "style": args.get("style", "电商带货"),
                "target_duration": args.get("target_duration", 15),
                "selected_materials": args.get("selected_materials", []),
            }
            # 检查是否启用本地工作流
            from sqlalchemy import select as _select
            from app.workflow.models import WorkflowConfig
            wf_q = await db.execute(
                _select(WorkflowConfig).where(
                    WorkflowConfig.user_id == user.id,
                    WorkflowConfig.workflow_name == "script-generate",
                )
            )
            wf_cfg = wf_q.scalar_one_or_none()
            if wf_cfg and wf_cfg.enabled:
                cfg = json.loads(wf_cfg.config or "{}")
                if cfg.get("api_key") and cfg.get("base_url") and cfg.get("model"):
                    from app.workflow.runners.script_generate import run_script_generate
                    result = await run_script_generate(
                        api_key=cfg["api_key"],
                        base_url=cfg["base_url"],
                        model=cfg["model"],
                        params=payload,
                    )
                else:
                    result = await call_workflow("script-generate", payload)
            else:
                result = await call_workflow("script-generate", payload)
            # 保存到 session_file
            script_json = json.dumps(result, ensure_ascii=False)
            sf = SessionFile(
                session_id=session_id, file_type="script",
                filename=f"script_{session_id}.json",
                file_url=f"/api/v1/agent/sessions/{session_id}/files/script",
                description="生成的剧本",
            )
            db.add(sf)
            await db.commit()
            return json.dumps(result, ensure_ascii=False, indent=2)
            await db.commit()
            return json.dumps(result, ensure_ascii=False, indent=2)

        elif tool_name == "generate_video":
            scenes = args.get("scenes", [])
            aspect_ratio = args.get("aspect_ratio", "9:16")
            for s in scenes:
                if "visual_desc" not in s and "visual_description" in s:
                    s["visual_desc"] = s.pop("visual_description")

            # 1. 查找素材URL并签发公网地址
            from app.material.models import Material
            from app.core.signer import generate_signed_url
            from sqlalchemy import select as _s2

            all_mids = set()
            for s in scenes:
                for mid in s.get("materials", []):
                    all_mids.add(mid)
            material_urls = {}
            if all_mids:
                mat_result = await db.execute(
                    _s2(Material).where(Material.id.in_(list(all_mids)))
                )
                for m in mat_result.scalars().all():
                    if m.image_url:
                        signed = generate_signed_url(m.image_url, expire_seconds=86400)
                        material_urls[m.id] = f"http://114.117.242.17:3000{signed}"

            # 2. 构建 reference_images
            for s in scenes:
                s["reference_images"] = [
                    {"url": material_urls[mid], "role": "reference_image"}
                    for mid in s.get("materials", []) if mid in material_urls
                ]
                if "lines" not in s:
                    s["lines"] = []

            # 3. 提交任务（完整script格式）
            result = await call_workflow("video-generate", {
                "workflow_type": "generate",
                "script": {
                    "title": args.get("title", f"视频_{session_id}"),
                    "style": args.get("style", "电商带货"),
                    "aspect_ratio": aspect_ratio,
                    "duration": sum(s.get("duration", 5) for s in scenes),
                    "scenes": scenes,
                },
            })
            logger.info("generate_raw_response", session_id=session_id, raw=json.dumps(result, ensure_ascii=False)[:500])
            # Coze 返回格式：{"result": {"task_ids": [...]}, "run_id": "..."}
            inner = result.get("result", result) if isinstance(result, dict) else result
            task_ids = inner.get("task_ids", []) if isinstance(inner, dict) else []
            if not task_ids:
                return json.dumps({"error": "提交视频生成任务失败，未获取到 task_ids"}, ensure_ascii=False)

            # 保存 task_ids
            sf = SessionFile(
                session_id=session_id, file_type="video_task",
                filename=f"tasks_{session_id}.json",
                file_url="",
                description=json.dumps(task_ids, ensure_ascii=False),
            )
            db.add(sf)
            await db.commit()

            # 2. 轮询等待（最多 30 分钟）
            deadline = time.monotonic() + 1800  # 30 min
            while time.monotonic() < deadline:
                await asyncio.sleep(30)
                try:
                    qr = await call_workflow("video-generate", {
                        "workflow_type": "query",
                        "task_ids": task_ids,
                    })
                    qr_inner = qr.get("result", qr) if isinstance(qr, dict) else qr
                    if isinstance(qr_inner, dict):
                        if qr_inner.get("status") == "completed":
                            clips = qr_inner.get("video_clips", [])
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
                            await db.commit()
                            return json.dumps(qr, ensure_ascii=False)
                        elif qr_inner.get("status") == "running":
                            continue  # 继续轮询
                except Exception as e:
                    logger.warning("poll_retry", session_id=session_id, error=str(e))
                    continue
            return json.dumps({"error": "视频生成超时（30分钟）"}, ensure_ascii=False)

        elif tool_name == "compose_video":
            # 从 SessionFile 读取已生成的视频片段和音频
            existing_files = await get_session_files(db, session_id)
            tts_files = [f for f in existing_files if f.file_type == "tts"]
            video_files = [f for f in existing_files if f.file_type == "video_clip"]
            # 如果只有一个 TTS 音频，给所有场景复用
            fallback_audio = tts_files[0].file_url if tts_files else ""
            scenes_for_compose = []
            full_text = args.get("script_text", "")
            for i, vf in enumerate(video_files):
                sid = vf.description.replace("场景 ", "").replace(" 视频片段", "") if vf.description else ""
                audio_url = ""
                for af in tts_files:
                    if sid and sid in (af.description or ""):
                        audio_url = af.file_url or ""
                        break
                if not audio_url:
                    audio_url = fallback_audio
                scenes_for_compose.append({
                    "scene_id": int(sid) if sid and sid.isdigit() else i + 1,
                    "video_url": vf.file_url or "",
                    "audio_url": audio_url,
                    "duration": 5,
                    "subtitle": full_text,
                })
            if not scenes_for_compose:
                # fallback: 用 args 中的 scenes
                scenes_for_compose = args.get("scenes", [])
            payload = {"scenes": scenes_for_compose}
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
                    description="最终合成视频",
                )
                db.add(sf)
                await db.commit()
            return json.dumps(result, ensure_ascii=False, indent=2)

        else:
            return json.dumps({"error": f"未知工具: {tool_name}"})
    except Exception as e:
        return json.dumps({"error": f"工具执行失败: {str(e)}"}, ensure_ascii=False)


# ── 聊天（含工具循环）────────────────────

@router.post("/sessions/{session_id}/chat")
async def agent_chat(
    session_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发送消息给 Agent，自动执行工具调用循环"""
    message = body.get("message", "")
    if not message:
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 保存用户消息
    user_msg = AgentMessage(session_id=session_id, role="user", content=message)
    db.add(user_msg)
    await db.commit()
    logger.info("chat_request", session_id=session_id, user_id=current_user.id, message_preview=message[:100])

    # 获取 AI 配置
    from app.ai.models import UserAIConfig
    config = await db.execute(select(UserAIConfig).where(UserAIConfig.user_id == current_user.id))
    config = config.scalar_one_or_none()
    if not config or not config.api_key:
        raise HTTPException(status_code=400, detail="请先在个人中心配置 AI API Key")

    # 工具循环 — 最多 10 轮
    import httpx
    history = await get_session_messages(db, session_id)

    for _round in range(10):
        # 构建 messages
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in history:
            if m.role == "tool":
                msgs.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content or ""})
            elif m.tool_calls:
                tc_list = json.loads(m.tool_calls)
                entry = {"role": "assistant", "content": m.content, "tool_calls": tc_list}
                if m.reasoning_content:
                    entry["reasoning_content"] = m.reasoning_content
                msgs.append(entry)
            else:
                entry = {"role": m.role, "content": m.content or ""}
                if m.reasoning_content:
                    entry["reasoning_content"] = m.reasoning_content
                msgs.append(entry)

        # 调 LLM
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": config.model,
            "messages": msgs,
            "tools": TOOLS_DEFINITIONS,
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{config.base_url.rstrip('/')}/chat/completions",
                    headers=headers, json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            detail = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    detail += " | body: " + e.response.text[:500]
                except Exception:
                    pass
            logger.error("llm_error", session_id=session_id, round=_round, error=detail)
            raise HTTPException(status_code=502, detail=f"AI 调用失败: {detail}")

        choice = data["choices"][0]
        msg = choice["message"]
        logger.info("llm_response", session_id=session_id, round=_round,
                    model=payload["model"], tool_calls=bool(msg.get("tool_calls")),
                    finish_reason=choice.get("finish_reason"))
        assistant_content = msg.get("content", "")
        reasoning = msg.get("reasoning_content") or msg.get("reasoning")
        tool_calls = msg.get("tool_calls")

        if not tool_calls:
            # 没有工具调用，返回最终答案
            assistant_msg = AgentMessage(
                session_id=session_id, role="assistant", content=assistant_content,
                reasoning_content=reasoning,
            )
            db.add(assistant_msg)
            await db.commit()
            await db.refresh(assistant_msg)
            return {
                "message": {
                    "id": assistant_msg.id,
                    "role": "assistant",
                    "content": assistant_content,
                    "tool_calls": None,
                },
                "finish_reason": choice.get("finish_reason"),
            }

        # 有工具调用 — 保存 assistant 消息
        tc_json = json.dumps([{
            "id": tc["id"],
            "type": "function",
            "function": {"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]}
        } for tc in tool_calls])
        assistant_msg = AgentMessage(
            session_id=session_id, role="assistant",
            content=assistant_content,
            reasoning_content=reasoning,
            tool_calls=tc_json,
        )
        db.add(assistant_msg)
        await db.commit()
        await db.refresh(assistant_msg)

        # 执行每个工具并保存结果
        for tc in tool_calls:
            func_name = tc["function"]["name"]
            try:
                raw_args = tc["function"]["arguments"]
                # 清理 LLM 常见的 JSON 错误：末尾逗号、多余换行
                import re as _re
                raw_args = _re.sub(r",\s*([}\]])", r"\1", raw_args)
                func_args = json.loads(raw_args)
                # 自动注入 session_id
                if "session_id" not in func_args:
                    func_args["session_id"] = session_id
                result_text = await execute_tool(func_name, func_args, db, session_id, current_user)
                logger.info("tool_executed", session_id=session_id, tool=func_name,
                            args_preview=str(func_args)[:200], result_preview=result_text[:200])
            except Exception as e:
                result_text = json.dumps({"error": str(e)}, ensure_ascii=False)
                logger.error("tool_error", session_id=session_id, tool=func_name, error=str(e))

            tool_msg = AgentMessage(
                session_id=session_id, role="tool",
                content=result_text,
                tool_call_id=tc["id"],
                tool_name=func_name,
            )
            db.add(tool_msg)
            await db.commit()

        # 刷新 history 进入下一轮
        history = await get_session_messages(db, session_id)

    # 超过 10 轮强制返回
    return {"message": {"role": "assistant", "content": "执行步骤过多，请重新描述需求"}, "finish_reason": "max_turns"}
