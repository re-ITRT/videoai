"""AI Agent 路由 — Session 管理 + 聊天 + 工具调用"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func
from app.core.database import get_db
from app.core.deps import get_current_user
from app.auth.models import User
from app.agent.models import (
    AgentSession, AgentMessage, SessionFile,
    SessionCreate, SessionResponse, MessageResponse, SessionFileResponse,
    create_session, list_sessions, get_session_messages, get_session_files,
)

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


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


# ── 聊天 ────────────────────────────────────

TOOLS_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "material_search",
            "description": "搜索素材库，按关键词查找已上传的图片/视频素材",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词，如'运动鞋'"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_script",
            "description": "为产品生成带货视频剧本",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string", "description": "产品名称"},
                    "product_desc": {"type": "string", "description": "产品描述"},
                    "duration": {"type": "integer", "description": "目标时长（秒）", "default": 15}
                },
                "required": ["product_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_tts",
            "description": "根据剧本旁白生成语音",
            "parameters": {
                "type": "object",
                "properties": {
                    "script_id": {"type": "integer", "description": "剧本ID"},
                    "session_id": {"type": "integer", "description": "当前Session ID"}
                },
                "required": ["script_id", "session_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_video",
            "description": "根据分镜描述生成视频片段",
            "parameters": {
                "type": "object",
                "properties": {
                    "script_id": {"type": "integer", "description": "剧本ID"},
                    "session_id": {"type": "integer", "description": "当前Session ID"},
                    "aspect_ratio": {"type": "string", "description": "画幅比例", "default": "9:16"}
                },
                "required": ["script_id", "session_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compose_video",
            "description": "将视频片段+音频+字幕合成为最终视频",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "integer", "description": "当前Session ID"},
                    "aspect_ratio": {"type": "string", "description": "画幅比例", "default": "9:16"}
                },
                "required": ["session_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_video",
            "description": "分析爆款视频，输出拆解报告",
            "parameters": {
                "type": "object",
                "properties": {
                    "video_url": {"type": "string", "description": "视频URL"}
                },
                "required": ["video_url"]
            }
        }
    },
]


@router.post("/sessions/{session_id}/chat")
async def agent_chat(
    session_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发送消息给 Agent，Agent 自动决定调用工具或对话"""
    message = body.get("message", "")
    if not message:
        raise HTTPException(status_code=400, detail="消息不能为空")

    # 保存用户消息
    user_msg = AgentMessage(session_id=session_id, role="user", content=message)
    db.add(user_msg)
    await db.commit()

    # 获取 AI 配置
    from app.ai.models import UserAIConfig
    config = await db.execute(select(UserAIConfig).where(UserAIConfig.user_id == current_user.id))
    config = config.scalar_one_or_none()
    if not config or not config.api_key:
        raise HTTPException(status_code=400, detail="请先在个人中心配置 AI API Key")

    # 构建 messages
    history = await get_session_messages(db, session_id)
    messages = [{"role": "system", "content": "你是 Video-AI 平台的 AI 助手。你可以调用工具来帮助用户完成视频创作。"
                "可调用的工具包括：素材搜索、剧本生成、语音合成、视频生成、视频合成、视频分析。"
        "\n\n当用户要求生成内容时：\n1. 先解释你要做什么\n2. 调用对应的工具\n3. 把工具返回的结果呈现给用户"}]
    for m in history:
        role = m.role
        if role == "tool":
            messages.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content or ""})
        elif m.tool_calls:
            tc_list = json.loads(m.tool_calls)
            messages.append({"role": "assistant", "content": m.content, "tool_calls": tc_list})
        else:
            messages.append({"role": role, "content": m.content or ""})

    # 调 LLM
    import httpx
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.model,
        "messages": messages,
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
        raise HTTPException(status_code=502, detail=f"AI 调用失败: {str(e)}")

    choice = data["choices"][0]
    msg = choice["message"]
    assistant_content = msg.get("content", "")
    tool_calls = msg.get("tool_calls")

    # 保存 assistant 消息
    assistant_msg = AgentMessage(
        session_id=session_id, role="assistant",
        content=assistant_content,
        tool_calls=json.dumps([{
            "id": tc["id"],
            "type": "function",
            "function": {"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]}
        } for tc in tool_calls]) if tool_calls else None,
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    return {
        "message": {
            "id": assistant_msg.id,
            "role": "assistant",
            "content": assistant_content,
            "tool_calls": tool_calls,
        },
        "finish_reason": choice.get("finish_reason"),
    }
