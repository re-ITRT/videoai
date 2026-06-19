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

# ── 覆盖 settings ──────────────────────────────
import app.config
app.config.settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"
app.config.settings.REDIS_URL = ""
app.config.settings.MINIO_ENDPOINT = ""
app.config.settings.CELERY_BROKER_URL = ""

# ── 修复 /app 不可写问题（WSL 环境）──
# 在导入 app.main 之前，先 patch os.makedirs 使其在创建 /app 目录时不报错
import os
import tempfile
_app_tmpdir = tempfile.mkdtemp(prefix="app_test_")
_original_makedirs = os.makedirs
def _patched_makedirs(path, mode=0o777, exist_ok=False):
    path_str = str(path)
    if path_str.startswith("/app"):
        redirected = path_str.replace("/app", _app_tmpdir, 1)
        return _original_makedirs(redirected, mode=mode, exist_ok=exist_ok)
    return _original_makedirs(path, mode=mode, exist_ok=exist_ok)
os.makedirs = _patched_makedirs

import builtins
_original_open = builtins.open
def _patched_open(path, mode='r', *args, **kwargs):
    if isinstance(path, str) and path.startswith("/app"):
        redirected = path.replace("/app", _app_tmpdir, 1)
        if 'w' in mode or 'a' in mode or os.path.exists(redirected):
            return _original_open(redirected, mode, *args, **kwargs)
        # 写操作或重定向文件存在时用重定向路径；读操作且重定向文件不存在时用原始路径
        return _original_open(path, mode, *args, **kwargs)
    # Handle PosixPath objects
    if hasattr(path, '__fspath__'):
        str_path = os.fspath(path)
        if str_path.startswith("/app"):
            redirected = str_path.replace("/app", _app_tmpdir, 1)
            if 'w' in mode or 'a' in mode or os.path.exists(redirected):
                return _original_open(redirected, mode, *args, **kwargs)
            return _original_open(redirected, mode, *args, **kwargs)
    return _original_open(path, mode, *args, **kwargs)
builtins.open = _patched_open

# Also patch os.mkdir (used by Path.mkdir) — swallow FileExistsError for /app paths
_original_mkdir = os.mkdir
def _patched_mkdir(path, mode=0o777, *, dir_fd=None):
    path_str = str(path)
    if path_str.startswith("/app"):
        redirected = path_str.replace("/app", _app_tmpdir, 1)
        try:
            return _original_mkdir(redirected, mode=mode, dir_fd=dir_fd)
        except FileExistsError:
            return None
    try:
        return _original_mkdir(path, mode=mode, dir_fd=dir_fd)
    except FileExistsError:
        return None
os.mkdir = _patched_mkdir

# Also patch StaticFiles to skip directory existence check
import starlette.staticfiles
_original_sf_init = starlette.staticfiles.StaticFiles.__init__
def _patched_sf_init(self, directory=None, *args, **kwargs):
    if directory and str(directory).startswith("/app"):
        directory = str(directory).replace("/app", _app_tmpdir, 1)
    return _original_sf_init(self, directory=directory, *args, **kwargs)
starlette.staticfiles.StaticFiles.__init__ = _patched_sf_init

# Ensure the temp /app/uploads directory exists before importing app.main
_original_makedirs(_app_tmpdir, mode=0o755, exist_ok=True)
_original_makedirs(os.path.join(_app_tmpdir, "uploads"), mode=0o755, exist_ok=True)


from app.main import app as fastapi_app
from app.core.database import Base, get_db


# ── 导入所有 models 让 Base.metadata 完整 ──
from app.auth.models import *  # noqa: F401, F403 (includes User)
from app.material.models import *  # noqa: F401, F403
from app.script.models import *  # noqa: F401, F403
from app.creation.models import *  # noqa: F401, F403
from app.published.models import *  # noqa: F401, F403


# ── A 的 fixture ──────────────────────────
@pytest.fixture
def sample_product_info():
    return {
        "id": 1,
        "name": "防晒喷雾",
        "category": "美妆",
        "features": ["轻薄不油腻", "防水防汗", "SPF50+"],
    }


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
