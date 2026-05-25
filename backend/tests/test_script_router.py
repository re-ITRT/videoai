"""
Tests for script router
"""
import pytest
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.script.router import router


class TestScriptRouterImports:
    def test_router_module_importable(self):
        """Test that the router module can be imported"""
        assert router is not None

    def test_router_has_correct_prefix(self):
        """Test that the router has the correct prefix"""
        assert router.prefix == "/scripts"

    def test_router_has_generate_endpoint(self):
        """Test that the router has generate endpoint"""
        routes = [route.path for route in router.routes]
        assert "/scripts/generate" in routes

    def test_router_tags(self):
        """Test router tags"""
        assert "scripts" in router.tags


class TestScriptRouterStructure:
    def test_endpoint_supports_post(self):
        """Test the generate endpoint supports POST method"""
        for route in router.routes:
            if "generate" in route.path:
                assert "POST" in route.methods
                break
        else:
            raise AssertionError("Generate route not found")

    def test_endpoint_has_handler(self):
        """Test that the endpoint has a handler function"""
        for route in router.routes:
            if "generate" in route.path:
                assert route.endpoint is not None
                break
        else:
            raise AssertionError("Generate route not found")

    def test_router_imports_schemas(self):
        """Test that router imports schemas correctly"""
        from app.script.schemas import ScriptGenerateRequest, ScriptGenerateResponse
        assert ScriptGenerateRequest is not None
        assert ScriptGenerateResponse is not None

    def test_router_imports_service(self):
        """Test that router imports generate_script correctly"""
        from app.script.service import generate_script
        assert generate_script is not None
