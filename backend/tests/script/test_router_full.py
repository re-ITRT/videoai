"""script/router.py 全覆盖测试"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException


class TestListScripts:
    @pytest.mark.asyncio
    async def test_list_scripts_empty(self, db_session):
        from app.script.router import list_scripts
        result = await list_scripts(db=db_session)
        assert result == []

    @pytest.mark.asyncio
    async def test_list_scripts_with_data(self, db_session):
        from app.script.router import list_scripts
        from app.script.models import Script
        s = Script(task_id=1, strategy="template", version="v1")
        db_session.add(s)
        await db_session.flush()
        result = await list_scripts(db=db_session)
        assert len(result) == 1
        assert result[0]["strategy"] == "template"


class TestGenerateScript:
    @pytest.mark.asyncio
    async def test_generate_success(self):
        from app.script.router import api_generate_script
        from app.script.schemas import ScriptGenerateRequest
        req = ScriptGenerateRequest(product_info={"name": "test"})
        with patch("app.script.router.generate_script", new_callable=AsyncMock) as gs:
            gs.return_value = {"script": "test script"}
            result = await api_generate_script(req)
            assert result["script"] == "test script"

    @pytest.mark.asyncio
    async def test_generate_error_500(self):
        from app.script.router import api_generate_script
        from app.script.schemas import ScriptGenerateRequest
        req = ScriptGenerateRequest(product_info={"name": "test"})
        with patch("app.script.router.generate_script", new_callable=AsyncMock,
                   side_effect=ValueError("something bad")):
            with pytest.raises(HTTPException) as exc:
                await api_generate_script(req)
            assert exc.value.status_code == 500
