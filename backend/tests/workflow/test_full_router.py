"""workflow/router.py 全覆盖测试 — 独立运行版
不依赖于 tests/conftest.py（避免 app.main import 失败），自行构建测试基础设施。
"""
import json
import os
import sys
import shutil
import tempfile
from unittest.mock import patch, AsyncMock, MagicMock
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import HTTPException

# ── 1. 提前 patch 设置 ─────────────────────────────
os.environ.setdefault("LOG_LEVEL", "ERROR")

import app.config
app.config.settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"
app.config.settings.REDIS_URL = ""
app.config.settings.MINIO_ENDPOINT = ""
app.config.settings.CELERY_BROKER_URL = ""

# ── 阻止 app.material.router 在 import 时创建 /app/uploads ──
import pathlib
_original_mkdir = pathlib.Path.mkdir

def _patched_mkdir(self, mode=0o777, parents=False, exist_ok=False):
    if str(self).startswith("/app"):
        return
    return _original_mkdir(self, mode, parents, exist_ok)

pathlib.Path.mkdir = _patched_mkdir

# ── 2. 导入所有必要模块 ────────────────────────────
from sqlalchemy import String, TypeDecorator, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.auth.models import User
from app.workflow.models import WorkflowConfig, WorkflowConfigUpdate, AVAILABLE_WORKFLOWS

# ── 3. SQLite JSONB 兼容 ────────────────────────────
class SQLiteJSONB(TypeDecorator):
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
    for klass in list(Base.registry._class_registry.values()):
        if not hasattr(klass, "__tablename__"):
            continue
        table = getattr(klass, "__table__", None)
        if table is None:
            continue
        for col in table.columns:
            if isinstance(col.type, JSONB):
                col.type = SQLiteJSONB()

_patch_jsonb_columns()


# ==============================================================
# 测试 Fixtures
# ==============================================================

@pytest_asyncio.fixture(scope="module")
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    # Clean up all data after each test
    async with factory() as session:
        meta = Base.metadata
        for table in reversed(meta.sorted_tables):
            await session.execute(table.delete())
        await session.commit()


async def _create_user(db_session, uid=1, username="testuser") -> User:
    user = User(
        id=uid, username=username, hashed_password="fakehash",
        is_active=True, role="user",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _temp_templates_dir(copy_default: bool = False) -> tuple[str, str]:
    """Create a temp directory, optionally copy the real 'default' template into it.
    Returns (temp_dir_path, original_TEMPLATES_DIR_path).
    Caller MUST call shutil.rmtree(temp_dir) in finally block.
    """
    from app.workflow.router import TEMPLATES_DIR as ORIG_TD
    tmp = tempfile.mkdtemp(prefix="test_templates_")
    if copy_default:
        src_default = os.path.join(ORIG_TD, "default")
        if os.path.isdir(src_default):
            shutil.copytree(src_default, os.path.join(tmp, "default"))
    return tmp, ORIG_TD


# ==============================================================
# GET /api/v1/workflows/available
# ==============================================================
class TestListAvailableWorkflows:
    @pytest.mark.asyncio
    async def test_returns_available_workflows(self):
        from app.workflow.router import list_available_workflows
        result = await list_available_workflows()
        assert "workflows" in result
        assert result["workflows"] is AVAILABLE_WORKFLOWS
        assert "script-generate" in result["workflows"]
        assert "video-generate" in result["workflows"]
        assert "asr-correct" in result["workflows"]


# ==============================================================
# GET /api/v1/workflows/configs
# ==============================================================
class TestListWorkflowConfigs:
    @pytest.mark.asyncio
    async def test_empty_configs(self, db_session):
        from app.workflow.router import list_workflow_configs
        user = await _create_user(db_session)
        result = await list_workflow_configs(db=db_session, current_user=user)
        assert result == []

    @pytest.mark.asyncio
    async def test_with_configs(self, db_session):
        from app.workflow.router import list_workflow_configs
        user = await _create_user(db_session)
        cfg = WorkflowConfig(
            user_id=user.id,
            workflow_name="script-generate",
            config='{"model": "deepseek-v4-flash"}',
            enabled=1,
        )
        db_session.add(cfg)
        await db_session.commit()

        result = await list_workflow_configs(db=db_session, current_user=user)
        assert len(result) == 1
        assert result[0].workflow_name == "script-generate"
        assert result[0].config == {"model": "deepseek-v4-flash"}
        assert result[0].enabled is True

    @pytest.mark.asyncio
    async def test_filters_by_user(self, db_session):
        from app.workflow.router import list_workflow_configs
        user1 = await _create_user(db_session, 1, "u1")
        user2 = await _create_user(db_session, 2, "u2")
        cfg = WorkflowConfig(user_id=1, workflow_name="script-generate", config="{}", enabled=1)
        db_session.add(cfg)
        await db_session.commit()
        r1 = await list_workflow_configs(db=db_session, current_user=user1)
        r2 = await list_workflow_configs(db=db_session, current_user=user2)
        assert len(r1) == 1
        assert len(r2) == 0

    @pytest.mark.asyncio
    async def test_config_json_parsing(self, db_session):
        from app.workflow.router import list_workflow_configs
        user = await _create_user(db_session)
        cfg = WorkflowConfig(
            user_id=user.id, workflow_name="test",
            config='{"api_key": "sk-xxx", "temperature": 0.3}', enabled=0,
        )
        db_session.add(cfg)
        await db_session.commit()
        result = await list_workflow_configs(db=db_session, current_user=user)
        assert result[0].config == {"api_key": "sk-xxx", "temperature": 0.3}
        assert result[0].enabled is False

    @pytest.mark.asyncio
    async def test_empty_config_string_returns_empty_dict(self, db_session):
        from app.workflow.router import list_workflow_configs
        user = await _create_user(db_session)
        cfg = WorkflowConfig(user_id=user.id, workflow_name="test", config="", enabled=1)
        db_session.add(cfg)
        await db_session.commit()
        result = await list_workflow_configs(db=db_session, current_user=user)
        assert result[0].config == {}


# ==============================================================
# GET /api/v1/workflows/configs/{workflow_name}
# ==============================================================
class TestGetWorkflowConfig:
    @pytest.mark.asyncio
    async def test_get_existing(self, db_session):
        from app.workflow.router import get_workflow_config
        user = await _create_user(db_session)
        cfg = WorkflowConfig(
            user_id=user.id, workflow_name="script-generate",
            config='{"model": "gpt-4"}', enabled=1,
        )
        db_session.add(cfg)
        await db_session.commit()
        result = await get_workflow_config(
            workflow_name="script-generate", db=db_session, current_user=user,
        )
        assert result.workflow_name == "script-generate"
        assert result.config == {"model": "gpt-4"}
        assert result.enabled is True

    @pytest.mark.asyncio
    async def test_get_non_existing_creates_new(self, db_session):
        from app.workflow.router import get_workflow_config
        user = await _create_user(db_session)
        result = await get_workflow_config(
            workflow_name="brand-new", db=db_session, current_user=user,
        )
        assert result.workflow_name == "brand-new"
        assert result.config == {}
        assert result.enabled is True
        r = await db_session.execute(
            select(WorkflowConfig).where(
                WorkflowConfig.user_id == user.id,
                WorkflowConfig.workflow_name == "brand-new",
            )
        )
        saved = r.scalar_one_or_none()
        assert saved is not None
        assert saved.config == "{}"

    @pytest.mark.asyncio
    async def test_get_null_config_returns_empty_dict(self, db_session):
        from app.workflow.router import get_workflow_config
        user = await _create_user(db_session)
        cfg = WorkflowConfig(
            user_id=user.id, workflow_name="null-cfg", config=None, enabled=0,
        )
        db_session.add(cfg)
        await db_session.commit()
        result = await get_workflow_config(
            workflow_name="null-cfg", db=db_session, current_user=user,
        )
        assert result.config == {}
        assert result.enabled is False


# ==============================================================
# PUT /api/v1/workflows/configs/{workflow_name}
# ==============================================================
class TestUpdateWorkflowConfig:
    @pytest.mark.asyncio
    async def test_update_config_only(self, db_session):
        from app.workflow.router import update_workflow_config
        user = await _create_user(db_session)
        cfg = WorkflowConfig(
            user_id=user.id, workflow_name="script-generate",
            config='{"model": "old"}', enabled=1,
        )
        db_session.add(cfg)
        await db_session.commit()
        upd = WorkflowConfigUpdate(config={"model": "new", "temperature": 0.8})
        result = await update_workflow_config(
            workflow_name="script-generate", update=upd,
            db=db_session, current_user=user,
        )
        assert result.config == {"model": "new", "temperature": 0.8}
        assert result.enabled is True

    @pytest.mark.asyncio
    async def test_update_enabled_only(self, db_session):
        from app.workflow.router import update_workflow_config
        user = await _create_user(db_session)
        cfg = WorkflowConfig(
            user_id=user.id, workflow_name="script-generate",
            config='{"model": "gpt"}', enabled=1,
        )
        db_session.add(cfg)
        await db_session.commit()
        upd = WorkflowConfigUpdate(enabled=False)
        result = await update_workflow_config(
            workflow_name="script-generate", update=upd,
            db=db_session, current_user=user,
        )
        assert result.config == {"model": "gpt"}
        assert result.enabled is False

    @pytest.mark.asyncio
    async def test_update_both_create_new(self, db_session):
        from app.workflow.router import update_workflow_config
        user = await _create_user(db_session)
        upd = WorkflowConfigUpdate(config={"k": "v"}, enabled=True)
        result = await update_workflow_config(
            workflow_name="new-flow", update=upd,
            db=db_session, current_user=user,
        )
        assert result.config == {"k": "v"}
        assert result.enabled is True

    @pytest.mark.asyncio
    async def test_update_none_values_keeps_existing(self, db_session):
        from app.workflow.router import update_workflow_config
        user = await _create_user(db_session)
        cfg = WorkflowConfig(
            user_id=user.id, workflow_name="script-generate",
            config='{"keep": "me"}', enabled=0,
        )
        db_session.add(cfg)
        await db_session.commit()
        upd = WorkflowConfigUpdate()
        result = await update_workflow_config(
            workflow_name="script-generate", update=upd,
            db=db_session, current_user=user,
        )
        assert result.config == {"keep": "me"}
        assert result.enabled is False


# ==============================================================
# GET /api/v1/workflows/prompts  — 依赖真实文件系统
# ==============================================================
class TestListAllTemplates:
    @pytest.mark.asyncio
    async def test_real_templates_dir_returns_templates(self):
        from app.workflow.router import list_all_templates
        result = await list_all_templates()
        assert "templates" in result
        assert "default" in result["templates"]
        assert "精细控制" in result["templates"]
        tmpl = result["templates"]["default"]
        assert tmpl["display_name"] == "默认带货模板"
        assert tmpl["tags"] == ["电商", "带货", "通用"]
        assert len(tmpl["prompt_preview"]) > 0

    @pytest.mark.asyncio
    async def test_templates_dir_not_exists(self):
        from app.workflow.router import list_all_templates
        with patch("os.path.isdir", return_value=False):
            result = await list_all_templates()
        assert result == {"templates": {}}

    @pytest.mark.asyncio
    async def test_template_without_info_json(self):
        from app.workflow.router import list_all_templates
        tmp, orig = _temp_templates_dir()
        test_dir = os.path.join(tmp, "__test_no_info")
        os.makedirs(test_dir, exist_ok=True)
        with open(os.path.join(test_dir, "system.md"), "w") as f:
            f.write("preview content")
        try:
            with patch("app.workflow.router.TEMPLATES_DIR", tmp):
                result = await list_all_templates()
            assert "__test_no_info" in result["templates"]
            tmpl = result["templates"]["__test_no_info"]
            assert tmpl["display_name"] == "__test_no_info"
            assert tmpl["description"] == ""
            assert tmpl["tags"] == []
            assert tmpl["prompt_preview"] == "preview content"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_template_without_system_md(self):
        from app.workflow.router import list_all_templates
        tmp, orig = _temp_templates_dir()
        test_dir = os.path.join(tmp, "__test_no_system")
        os.makedirs(test_dir, exist_ok=True)
        with open(os.path.join(test_dir, "template_info.json"), "w") as f:
            json.dump({"name": "NoSystem", "description": "desc"}, f)
        try:
            with patch("app.workflow.router.TEMPLATES_DIR", tmp):
                result = await list_all_templates()
            assert "__test_no_system" in result["templates"]
            tmpl = result["templates"]["__test_no_system"]
            assert tmpl["display_name"] == "NoSystem"
            assert tmpl["description"] == "desc"
            assert tmpl["prompt_preview"] == ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_skips_non_directory_entries(self):
        from app.workflow.router import list_all_templates
        tmp, orig = _temp_templates_dir()
        test_file = os.path.join(tmp, "__test_file_entry.txt")
        try:
            with open(test_file, "w") as f:
                f.write("not a dir")
            with patch("app.workflow.router.TEMPLATES_DIR", tmp):
                result = await list_all_templates()
            assert "__test_file_entry.txt" not in result["templates"]
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)
            shutil.rmtree(tmp, ignore_errors=True)


# ==============================================================
# GET /api/v1/workflows/prompts/output-format
# ==============================================================
class TestGetOutputFormat:
    @pytest.mark.asyncio
    async def test_file_exists(self):
        from app.workflow.router import get_output_format
        result = await get_output_format()
        assert "content" in result
        assert "输出格式" in result["content"]

    @pytest.mark.asyncio
    async def test_file_not_exists(self):
        from app.workflow.router import get_output_format
        with patch("os.path.exists", return_value=False):
            result = await get_output_format()
        assert result == {"content": ""}


# ==============================================================
# GET /api/v1/workflows/prompts/{workflow_name}
# ==============================================================
class TestGetWorkflowPrompts:
    @pytest.mark.asyncio
    async def test_from_templates_dir(self):
        from app.workflow.router import get_workflow_prompts
        result = await get_workflow_prompts(workflow_name="default")
        assert "files" in result
        assert "system.md" in result["files"]
        assert "template_info.json" in result["files"]
        assert "user.md.j2" in result["files"]

    @pytest.mark.asyncio
    async def test_from_prompts_root_dir(self):
        from app.workflow.router import get_workflow_prompts
        result = await get_workflow_prompts(workflow_name="script_generate")
        assert "files" in result
        assert "system.md" in result["files"]
        assert "user.md.j2" in result["files"]

    @pytest.mark.asyncio
    async def test_not_found_returns_empty(self):
        from app.workflow.router import get_workflow_prompts
        result = await get_workflow_prompts(workflow_name="__nonexistent_xyz__")
        assert result == {"files": {}}


# ==============================================================
# PUT /api/v1/workflows/prompts/{workflow_name}/{filename}
# ==============================================================
class TestUpdateWorkflowPrompt:
    @pytest.mark.asyncio
    async def test_invalid_extension_400(self):
        from app.workflow.router import update_workflow_prompt
        with pytest.raises(HTTPException) as exc:
            await update_workflow_prompt(
                workflow_name="default", filename="script.py", body={"content": "test"},
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_creates_new_file(self):
        from app.workflow.router import update_workflow_prompt
        tmp, orig = _temp_templates_dir(copy_default=True)
        fpath = os.path.join(tmp, "default", "__test_new.j2")
        try:
            with patch("app.workflow.router.TEMPLATES_DIR", tmp):
                result = await update_workflow_prompt(
                    workflow_name="default", filename="__test_new.j2",
                    body={"content": "hello"},
                )
            assert result == {"ok": True}
            assert os.path.isfile(fpath)
            with open(fpath) as f:
                assert f.read() == "hello"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_overwrites_existing(self):
        from app.workflow.router import update_workflow_prompt
        tmp, orig = _temp_templates_dir(copy_default=True)
        fpath = os.path.join(tmp, "default", "__test_overwrite.j2")
        try:
            with open(fpath, "w") as f:
                f.write("old")
            with patch("app.workflow.router.TEMPLATES_DIR", tmp):
                result = await update_workflow_prompt(
                    workflow_name="default", filename="__test_overwrite.j2",
                    body={"content": "new"},
                )
            assert result == {"ok": True}
            with open(fpath) as f:
                assert f.read() == "new"
        finally:
            if os.path.exists(fpath):
                os.remove(fpath)
            shutil.rmtree(tmp, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_empty_body_writes_empty(self):
        from app.workflow.router import update_workflow_prompt
        tmp, orig = _temp_templates_dir(copy_default=True)
        fpath = os.path.join(tmp, "default", "__test_empty.j2")
        try:
            with patch("app.workflow.router.TEMPLATES_DIR", tmp):
                result = await update_workflow_prompt(
                    workflow_name="default", filename="__test_empty.j2", body={},
                )
            assert result == {"ok": True}
            with open(fpath) as f:
                assert f.read() == ""
        finally:
            if os.path.exists(fpath):
                os.remove(fpath)
            shutil.rmtree(tmp, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_writes_to_templates_dir_by_default(self):
        """Router code always breaks on TEMPLATES_DIR iteration"""
        from app.workflow.router import update_workflow_prompt
        tmp, orig = _temp_templates_dir()
        fpath = os.path.join(tmp, "__test_root_dir", "__test_root.j2")
        try:
            with patch("app.workflow.router.TEMPLATES_DIR", tmp):
                result = await update_workflow_prompt(
                    workflow_name="__test_root_dir", filename="__test_root.j2",
                    body={"content": "root"},
                )
            assert result == {"ok": True}
            assert os.path.isfile(fpath)
            with open(fpath) as f:
                assert f.read() == "root"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ==============================================================
# POST /api/v1/workflows/templates
# ==============================================================
class TestCreateTemplate:
    @pytest.mark.asyncio
    async def test_create_success(self):
        from app.workflow.router import create_template
        tmp, orig = _temp_templates_dir(copy_default=True)
        name = "__test_create_ok"
        dst = os.path.join(tmp, name)
        try:
            if os.path.exists(dst):
                shutil.rmtree(dst)
            with patch("app.workflow.router.TEMPLATES_DIR", tmp):
                result = await create_template(body={"name": name})
            assert result == {"ok": True, "name": name}
            assert os.path.isdir(dst)
            assert os.path.isfile(os.path.join(dst, "system.md"))
            with open(os.path.join(dst, "template_info.json")) as f:
                info = json.load(f)
                assert info["name"] == name
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_empty_name_400(self):
        from app.workflow.router import create_template
        with pytest.raises(HTTPException) as exc:
            await create_template(body={"name": "  "})
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_name_400(self):
        from app.workflow.router import create_template
        with pytest.raises(HTTPException) as exc:
            await create_template(body={})
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_existing_name_400(self):
        from app.workflow.router import create_template
        with pytest.raises(HTTPException) as exc:
            await create_template(body={"name": "default"})
        assert exc.value.status_code == 400


# ==============================================================
# DELETE /api/v1/workflows/templates/{template_name}
# ==============================================================
class TestDeleteTemplate:
    @pytest.mark.asyncio
    async def test_delete_default_400(self):
        from app.workflow.router import delete_template
        with pytest.raises(HTTPException) as exc:
            await delete_template(template_name="default")
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_nonexistent_404(self):
        from app.workflow.router import delete_template
        with pytest.raises(HTTPException) as exc:
            await delete_template(template_name="__nonexistent_xyz__")
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_success(self):
        from app.workflow.router import delete_template
        tmp, orig = _temp_templates_dir(copy_default=True)
        name = "__test_delete_ok"
        dst = os.path.join(tmp, name)
        src_default = os.path.join(tmp, "default")
        shutil.copytree(src_default, dst)
        try:
            with patch("app.workflow.router.TEMPLATES_DIR", tmp):
                result = await delete_template(template_name=name)
            assert result == {"ok": True}
            assert not os.path.exists(dst)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ==============================================================
# POST /api/v1/workflows/configs/{workflow_name}/scan-models
# ==============================================================
class TestScanWorkflowModels:
    @pytest.mark.asyncio
    async def test_scan_success_with_existing_key(self, db_session):
        from app.workflow.router import scan_workflow_models
        user = await _create_user(db_session)
        cfg = WorkflowConfig(
            user_id=user.id, workflow_name="script-generate",
            config='{"api_key": "sk-test", "base_url": "https://api.test.com/v1"}',
        )
        db_session.add(cfg)
        await db_session.commit()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [{"id": "m1"}, {"id": "m2"}]
        }
        # raise_for_status is a sync method on httpx.Response
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_resp

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await scan_workflow_models(
                workflow_name="script-generate", body={},
                db=db_session, current_user=user,
            )

        assert result["models"] == ["m1", "m2"]
        assert result["selected"] == "m1"
        await db_session.refresh(cfg)
        saved = json.loads(cfg.config)
        assert saved["available_models"] == ["m1", "m2"]

    @pytest.mark.asyncio
    async def test_scan_body_overrides_config(self, db_session):
        from app.workflow.router import scan_workflow_models
        user = await _create_user(db_session)
        cfg = WorkflowConfig(
            user_id=user.id, workflow_name="script-generate",
            config='{"api_key": "old-key", "base_url": "https://old.api.com/v1"}',
        )
        db_session.add(cfg)
        await db_session.commit()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"id": "custom-model"}]}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_resp

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await scan_workflow_models(
                workflow_name="script-generate",
                body={"base_url": "https://custom.api.com/v1", "api_key": "custom-key"},
                db=db_session, current_user=user,
            )

        assert result["models"] == ["custom-model"]
        call_url = mock_client.get.call_args[0][0]
        assert "custom.api.com" in call_url

    @pytest.mark.asyncio
    async def test_scan_no_api_key_400(self, db_session):
        from app.workflow.router import scan_workflow_models
        user = await _create_user(db_session)
        cfg = WorkflowConfig(user_id=user.id, workflow_name="script-generate", config="{}")
        db_session.add(cfg)
        await db_session.commit()
        with pytest.raises(HTTPException) as exc:
            await scan_workflow_models(
                workflow_name="script-generate", body={},
                db=db_session, current_user=user,
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_scan_http_status_error_502(self, db_session):
        import httpx
        from app.workflow.router import scan_workflow_models
        user = await _create_user(db_session)
        cfg = WorkflowConfig(
            user_id=user.id, workflow_name="script-generate",
            config='{"api_key": "sk-test"}',
        )
        db_session.add(cfg)
        await db_session.commit()

        async def mock_get(url, **kwargs):
            resp = MagicMock(status_code=401)
            raise httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=resp)

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get = mock_get

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc:
                await scan_workflow_models(
                    workflow_name="script-generate", body={},
                    db=db_session, current_user=user,
                )
        assert exc.value.status_code == 502

    @pytest.mark.asyncio
    async def test_scan_connection_error_502(self, db_session):
        from app.workflow.router import scan_workflow_models
        user = await _create_user(db_session)
        cfg = WorkflowConfig(
            user_id=user.id, workflow_name="script-generate",
            config='{"api_key": "sk-test"}',
        )
        db_session.add(cfg)
        await db_session.commit()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.side_effect = Exception("Connection refused")

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(HTTPException) as exc:
                await scan_workflow_models(
                    workflow_name="script-generate", body={},
                    db=db_session, current_user=user,
                )
        assert exc.value.status_code == 502

    @pytest.mark.asyncio
    async def test_video_generate_returns_hardcoded_ep(self, db_session):
        from app.workflow.router import scan_workflow_models
        user = await _create_user(db_session)
        cfg = WorkflowConfig(
            user_id=user.id, workflow_name="video-generate",
            config='{"api_key": "ark-test"}',
        )
        db_session.add(cfg)
        await db_session.commit()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"id": "m"}]}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_resp

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await scan_workflow_models(
                workflow_name="video-generate", body={},
                db=db_session, current_user=user,
            )

        assert len(result["models"]) == 1
        assert "Doubao-Seedance-1.5-pro" in result["models"][0]
        assert result["selected"] == "ep-20260514120705-pqv86"

    @pytest.mark.asyncio
    async def test_empty_data_uses_empty_selected(self, db_session):
        from app.workflow.router import scan_workflow_models
        user = await _create_user(db_session)
        cfg = WorkflowConfig(
            user_id=user.id, workflow_name="script-generate",
            config='{"api_key": "sk-test"}',
        )
        db_session.add(cfg)
        await db_session.commit()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": []}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_resp

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await scan_workflow_models(
                workflow_name="script-generate", body={},
                db=db_session, current_user=user,
            )
        assert result["models"] == []
        assert result["selected"] == ""

    @pytest.mark.asyncio
    async def test_model_from_config_used_as_selected(self, db_session):
        from app.workflow.router import scan_workflow_models
        user = await _create_user(db_session)
        cfg = WorkflowConfig(
            user_id=user.id, workflow_name="script-generate",
            config='{"api_key": "sk-test", "model": "gpt-4"}',
        )
        db_session.add(cfg)
        await db_session.commit()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"id": "gpt-4"}, {"id": "gpt-3.5"}]}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_resp

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await scan_workflow_models(
                workflow_name="script-generate", body={},
                db=db_session, current_user=user,
            )
        assert result["selected"] == "gpt-4"
