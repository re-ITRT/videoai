from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.auth.router import router as auth_router
from app.material.router import router as material_router
from app.script.router import router as script_router
from app.workflow.router import router as workflow_config_router
from app.creation.router import router as creation_router
from app.user.router import router as user_router
from app.workers.router import router as workflow_router
from app.reference.router import router as reference_router
from app.template.router import router as template_router
from app.review import router as review_router
from app.metrics.router import router as metrics_router
from app.signed import router as signed_router
from app.material.embed_view import router as embed_router
from app.ai.router import router as ai_router
from app.agent.router import router as agent_router
from app.studio.router import router as studio_router

# ── 初始化日志 ──────────────────────────
from app.core.logging import setup_logging
from app.core.database import engine, Base, async_session
from app.config import settings
from sqlalchemy import text
import asyncio

setup_logging()

app = FastAPI(title="Video-AI API", version="0.1.0", docs_url="/docs")


@app.on_event("startup")
async def startup():
    # 确保 video_ai 数据库存在（Docker 重启后可能丢失）
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        tmp_engine = create_async_engine(
            settings.DATABASE_URL.replace("/video_ai", "/postgres"),
            isolation_level="AUTOCOMMIT",
        )
        async with tmp_engine.begin() as conn:
            row = await conn.execute(text("SELECT 1 FROM pg_database WHERE datname='video_ai'"))
            if not row.scalar():
                await conn.execute(text("CREATE DATABASE video_ai"))
        await tmp_engine.dispose()
    except Exception as e:
        print(f"DB init warning: {e}")

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE materials ADD COLUMN IF NOT EXISTS embedding vector(1024)"))
        await conn.execute(text("ALTER TABLE material_slices ADD COLUMN IF NOT EXISTS embedding vector(1024)"))
    # 确保默认账号存在
    try:
        from app.auth.models import User
        from passlib.hash import bcrypt
        async with async_session() as s:
            r = await s.execute(text("SELECT 1 FROM users WHERE username='admin'"))
            if not r.scalar():
                s.add(User(username="admin", hashed_password=bcrypt.hash("Admin123"), role="admin"))
                s.add(User(username="testuser", hashed_password=bcrypt.hash("Test12345"), role="user"))
                await s.commit()
                print("Default accounts created")
    except Exception as e:
        print(f"Account init warning: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(material_router)
app.include_router(script_router)
app.include_router(workflow_config_router)
app.include_router(creation_router)
app.include_router(user_router)
app.include_router(workflow_router)
app.include_router(reference_router)
app.include_router(template_router)
app.include_router(review_router)
app.include_router(metrics_router)
app.include_router(signed_router)
app.include_router(embed_router)
app.include_router(ai_router)
app.include_router(agent_router)
app.include_router(studio_router)

# ── 静态文件 ──────────────────────────
import os
uploads_dir = "/app/uploads"
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
