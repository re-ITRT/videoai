"""工作流模块测试"""
import pytest


class TestWorkflowConfig:
    """验证工作流配置完整性"""

    def test_workflow_tokens_present(self):
        from app.workers.workflow import WORKFLOW_TOKENS, WORKFLOW_URLS
        assert len(WORKFLOW_TOKENS) == 7
        assert len(WORKFLOW_URLS) == 7
        assert set(WORKFLOW_TOKENS.keys()) == set(WORKFLOW_URLS.keys())

    def test_workflow_urls_end_with_run(self):
        from app.workers.workflow import WORKFLOW_URLS
        for name, url in WORKFLOW_URLS.items():
            assert url.endswith("/run"), f"{name}: {url} must end with /run"

    def test_workflow_tokens_are_jwt(self):
        from app.workers.workflow import WORKFLOW_TOKENS
        for name, token in WORKFLOW_TOKENS.items():
            parts = token.split(".")
            assert len(parts) == 3, f"{name}: token must have 3 parts (JWT)"
            assert len(parts[0]) > 10, f"{name}: header too short"

    def test_list_workflows(self):
        from app.workers.workflow import AVAILABLE_WORKFLOWS
        expected = [
            "material-embed", "query-generate", "material-search",
            "script-generate", "tts-generate", "video-generate", "video-compose",
        ]
        assert sorted(AVAILABLE_WORKFLOWS) == sorted(expected)

    def test_call_unknown_workflow(self):
        from app.workers.workflow import call_workflow
        import pytest
        with pytest.raises(ValueError, match="未知工作流"):
            import asyncio
            asyncio.run(call_workflow("unknown", {}))

    def test_module_imports(self):
        from app.workers.workflow import WORKFLOW_TIMEOUT
        assert WORKFLOW_TIMEOUT == 120

    def test_token_uniqueness(self):
        """每个工作流 token 不同"""
        from app.workers.workflow import WORKFLOW_TOKENS
        tokens = list(WORKFLOW_TOKENS.values())
        assert len(set(tokens)) == 7, "Tokens must be unique per workflow"


class TestWorkflowRouter:

    @pytest.mark.asyncio
    async def test_list_workflows_endpoint(self, client):
        resp = await client.get("/api/v1/workflows")
        assert resp.status_code == 200
        data = resp.json()
        assert "workflows" in data
        assert len(data["workflows"]) == 7

    @pytest.mark.asyncio
    async def test_run_unknown_workflow(self, client):
        resp = await client.post("/api/v1/workflows/unknown/run", json={})
        assert resp.status_code == 404
        assert "未知工作流" in resp.text
