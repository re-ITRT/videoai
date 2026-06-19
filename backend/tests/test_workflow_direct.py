"""工作流直接测试 — 覆盖 call_workflow 函数"""
import pytest
import httpx


class TestWorkflowCallDirect:
    """直接测试 call_workflow (mock httpx)"""

    @pytest.mark.asyncio
    async def test_call_workflow_success(self):
        from app.workers.workflow import call_workflow

        async def mock_handler(request):
            return httpx.Response(200, json={"code": 0, "data": {"result": "ok"}})

        # Patch the httpx client in the workflow module
        import app.workers.workflow as wf

        original_timeout = wf.WORKFLOW_TIMEOUT
        async with httpx.AsyncClient(transport=httpx.MockTransport(mock_handler)) as client:
            # Temporarily replace httpx.AsyncClient
            import importlib
            from unittest.mock import patch

            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = mock_client.return_value
                mock_instance.__aenter__.return_value = client
                mock_instance.__aexit__.return_value = None

                result = await call_workflow("material-embed", {"test": True})
                assert result == {"code": 0, "data": {"result": "ok"}}

    @pytest.mark.asyncio
    async def test_call_workflow_sends_auth(self):
        """验证发送了 Bearer token"""
        from app.workers.workflow import call_workflow, WORKFLOW_TOKENS

        sent_headers = {}

        async def mock_handler(request):
            nonlocal sent_headers
            sent_headers = dict(request.headers)
            return httpx.Response(200, json={"ok": True})

        async with httpx.AsyncClient(transport=httpx.MockTransport(mock_handler)) as client:
            from unittest.mock import patch
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = mock_client.return_value
                mock_instance.__aenter__.return_value = client
                mock_instance.__aexit__.return_value = None

                await call_workflow("query-generate", {"q": "test"})

            auth_header = sent_headers.get("authorization") or sent_headers.get("Authorization", "")
            assert auth_header.startswith("Bearer ")
            # Verify it's the correct token
            expected_token = WORKFLOW_TOKENS["query-generate"]
            assert auth_header == f"Bearer {expected_token}"

    @pytest.mark.asyncio
    async def test_call_workflow_all_workflows(self):
        """验证每个工作流都能构造请求"""
        from app.workers.workflow import call_workflow, WORKFLOW_TOKENS, WORKFLOW_URLS

        called = []

        async def handler(request):
            called.append(request.url)
            return httpx.Response(200, json={"ok": True})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            from unittest.mock import patch
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = mock_client.return_value
                mock_instance.__aenter__.return_value = client
                mock_instance.__aexit__.return_value = None

                for name in WORKFLOW_URLS:
                    await call_workflow(name, {"p": name})

        assert len(called) == 8
        for name, url in WORKFLOW_URLS.items():
            assert any(url in str(u) for u in called), f"{name}: {url} not called"

    @pytest.mark.asyncio
    async def test_call_workflow_http_error(self):
        """HTTP 错误应抛出"""
        from app.workers.workflow import call_workflow

        async def handler(request):
            return httpx.Response(500, json={"error": "server error"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            from unittest.mock import patch
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = mock_client.return_value
                mock_instance.__aenter__.return_value = client
                mock_instance.__aexit__.return_value = None

                with pytest.raises(Exception):
                    await call_workflow("material-embed", {"test": True})
