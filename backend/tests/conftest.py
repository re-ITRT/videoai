"""
测试基础设施 — 异步 FastAPI + SQLite 内存数据库
"""
import json
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import String, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app as fastapi_app
from app.core.database import Base, get_db

# ── 导入所有 models 让 Base.metadata 完整 ──
from app.auth.models import *  # noqa: F401, F403 (includes User)
from app.material.models import *  # noqa: F401, F403
from app.script.models import *  # noqa: F401, F403
from app.creation.models import *  # noqa: F401, F403


# ── 覆盖 settings ──────────────────────────────
import app.config
app.config.settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"
app.config.settings.REDIS_URL = ""
app.config.settings.MINIO_ENDPOINT = ""
app.config.settings.CELERY_BROKER_URL = ""


# ── SQLite 兼容 JSONB ──────────────────────────
class SQLiteJSONB(TypeDecorator):
    """让 JSONB 能在 SQLite 上跑"""
    impl = String

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(String)
        return dialect.type_descriptor(JSONB)

    def process_bind_param(self, value, dialect):
        if dialect.name == "sqlite":
            return json.dumps(value, ensure_ascii=False) if value is not None else None
        return value

    def process_result_value(self, value, dialect):
        if dialect.name == "sqlite":
            return json.loads(value) if value is not None else None
        return value


def _patch_jsonb_columns():
    """递归替换所有 Base 模型的 JSONB 列为 SQLiteJSONB"""
    for klass in Base.registry._class_registry.values():
        if not hasattr(klass, "__tablename__"):
            continue
        table = getattr(klass, "__table__", None)
        if table is None:
            continue
        for col in table.columns:
            if isinstance(col.type, JSONB):
                col.type = SQLiteJSONB()


# ── Engine & session ───────────────────────────
@pytest_asyncio.fixture(scope="session")
async def engine():
    _patch_jsonb_columns()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """提供 AsyncClient，自动使用测试 DB"""

    async def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()
