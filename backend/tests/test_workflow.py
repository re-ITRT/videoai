"""
Tests for workflow integration
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.workers.workflow import call_workflow, WORKFLOW_TOKENS


class TestWorkflowTokens:
    def test_all_workflows_configured(self):
        expected_workflows = {
            "query-generate",
            "material-embed",
            "material-search",
            "script-generate",
            "tts-generate",
            "video-generate",
            "video-compose",
            "video-analyze",
        }
        assert set(WORKFLOW_TOKENS.keys()) == expected_workflows

    def test_tokens_not_empty(self):
        for workflow, token in WORKFLOW_TOKENS.items():
            assert token is not None
            assert len(token) > 0
            assert not token.isspace()


class MockResponse:
    def __init__(self, json_data, raise_error=False):
        self.json_data = json_data
        self.raise_error = raise_error

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.raise_error:
            raise Exception("HTTP Error")


class TestCallWorkflow:
    @pytest.mark.asyncio
    async def test_call_workflow_success(self):
        mock_response_data = {
            "scenes": [
                {"id": 1, "order": 1, "description": "test", "narration": "test", "duration": 5}
            ]
        }

        with patch("app.workers.workflow.httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=MockResponse(mock_response_data))
            mock_context = MagicMock()
            mock_context.__aenter__.return_value.post = mock_post
            mock_client.return_value = mock_context

            # Call
            payload = {"product_info": {"name": "test"}}
            result = await call_workflow("script-generate", payload)

            # Verify
            assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_call_workflow_unknown_name(self):
        with pytest.raises(ValueError, match="未知工作流"):
            await call_workflow("unknown-workflow", {})

    @pytest.mark.asyncio
    async def test_call_workflow_http_error(self):
        with patch("app.workers.workflow.httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=MockResponse({}, raise_error=True))
            mock_context = MagicMock()
            mock_context.__aenter__.return_value.post = mock_post
            mock_client.return_value = mock_context

            with pytest.raises(Exception, match="HTTP Error"):
                await call_workflow("script-generate", {})

    @pytest.mark.asyncio
    async def test_call_workflow_with_custom_payload(self):
        with patch("app.workers.workflow.httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=MockResponse({}))
            mock_context = MagicMock()
            mock_context.__aenter__.return_value.post = mock_post
            mock_client.return_value = mock_context

            payload = {
                "product_info": {"id": 1, "name": "防晒喷雾"},
                "target_duration": 30,
                "style": "lifestyle",
            }

            await call_workflow("script-generate", payload)

            # Verify the payload was passed correctly
            call_args = mock_post.call_args
            sent_payload = call_args.kwargs["json"]
            assert sent_payload["product_info"]["name"] == "防晒喷雾"
            assert sent_payload["target_duration"] == 30

    @pytest.mark.asyncio
    async def test_workflow_token_passed_in_header(self):
        with patch("app.workers.workflow.httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=MockResponse({}))
            mock_context = MagicMock()
            mock_context.__aenter__.return_value.post = mock_post
            mock_client.return_value = mock_context

            await call_workflow("script-generate", {})

            # Verify Authorization header
            call_args = mock_post.call_args
            headers = call_args.kwargs["headers"]
            assert "Authorization" in headers
            assert headers["Authorization"].startswith("Bearer ")
            assert len(headers["Authorization"]) > len("Bearer ")

    @pytest.mark.asyncio
    async def test_all_workflow_names_callable(self):
        """Test that all configured workflow names don't raise ValueError"""
        workflow_names = list(WORKFLOW_TOKENS.keys())

        with patch("app.workers.workflow.httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=MockResponse({}))
            mock_context = MagicMock()
            mock_context.__aenter__.return_value.post = mock_post
            mock_client.return_value = mock_context

            for workflow_name in workflow_names:
                # This should not raise ValueError
                await call_workflow(workflow_name, {})
