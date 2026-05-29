"""AI Agent — Session + 消息 + 工具调用"""
import json
import os
import shutil
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.database import Base


# ── 数据库模型 ─────────────────────────────

class AgentSession(Base):
    """AI 对话 Session"""
    __tablename__ = "agent_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    title = Column(String(256), default="新对话")
    session_dir = Column(String(512))  # 文件存储路径
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AgentMessage(Base):
    """对话消息"""
    __tablename__ = "agent_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(32), nullable=False)  # user / assistant / tool
    content = Column(Text)
    tool_calls = Column(Text)  # JSON: [{name, arguments}]
    tool_call_id = Column(String(64))
    tool_name = Column(String(64))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SessionFile(Base):
    """Session 生成的文件（tts/video/成品）"""
    __tablename__ = "session_files"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False)
    file_type = Column(String(32), nullable=False)  # tts / video_clip / final_video / material / script
    filename = Column(String(256))
    file_url = Column(Text)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ── Pydantic Schema ────────────────────────

class SessionCreate(BaseModel):
    title: str = "新对话"


class SessionResponse(BaseModel):
    id: int
    title: str
    message_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    role: str
    content: Optional[str] = None
    tool_calls: Optional[list] = None
    created_at: datetime


class SessionFileResponse(BaseModel):
    id: int
    file_type: str
    filename: Optional[str] = None
    file_url: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


# ── 文件系统 ───────────────────────────────

SESSION_ROOT = "/app/uploads/agent_sessions"


def ensure_session_dir(session_id: int) -> dict[str, str]:
    """创建 session 文件夹结构"""
    base = os.path.join(SESSION_ROOT, str(session_id))
    dirs = {
        "root": base,
        "tts": os.path.join(base, "tts"),
        "video_clips": os.path.join(base, "video_clips"),
        "final_videos": os.path.join(base, "final_videos"),
        "materials": os.path.join(base, "materials"),
        "scripts": os.path.join(base, "scripts"),
    }
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)
    return dirs


# ── 服务函数 ───────────────────────────────

async def create_session(db: AsyncSession, user_id: int, title: str = "新对话") -> AgentSession:
    sess = AgentSession(user_id=user_id, title=title)
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    # 创建文件夹
    dirs = ensure_session_dir(sess.id)
    sess.session_dir = json.dumps(dirs)
    await db.commit()
    return sess


async def list_sessions(db: AsyncSession, user_id: int) -> list[AgentSession]:
    result = await db.execute(
        select(AgentSession)
        .where(AgentSession.user_id == user_id)
        .order_by(AgentSession.updated_at.desc())
    )
    return list(result.scalars().all())


async def delete_session(db: AsyncSession, session_id: int, user_id: int) -> bool:
    """删除 Session（含级联消息/文件 + 物理目录）"""
    result = await db.execute(
        select(AgentSession).where(AgentSession.id == session_id, AgentSession.user_id == user_id)
    )
    sess = result.scalar_one_or_none()
    if not sess:
        return False
    await db.delete(sess)
    await db.commit()
    # 清理物理目录
    if sess.session_dir:
        try:
            root = json.loads(sess.session_dir)["root"]
            if os.path.exists(root):
                shutil.rmtree(root)
        except Exception:
            pass
    return True


async def get_session_messages(db: AsyncSession, session_id: int) -> list[AgentMessage]:
    result = await db.execute(
        select(AgentMessage)
        .where(AgentMessage.session_id == session_id)
        .order_by(AgentMessage.id)
    )
    return list(result.scalars().all())


async def get_session_files(db: AsyncSession, session_id: int) -> list[SessionFile]:
    result = await db.execute(
        select(SessionFile)
        .where(SessionFile.session_id == session_id)
        .order_by(SessionFile.created_at.desc())
    )
    return list(result.scalars().all())
