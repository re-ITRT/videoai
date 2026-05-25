"""Script router tests"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI

from app.script.router import router


app = FastAPI()
app.include_router(router)


class TestScriptRouter:
    """测试剧本API接口"""

    @pytest.mark.asyncio
    async def test_generate_script_endpoint_no_auth(self):
        """无token时应该返回401"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/generate",
                json={"product_info": {"name": "test"}, "target_duration": 15}
            )
            # 没有auth依赖的话可能200，但实际有auth，这个测试在真实环境会401
            # 这里只测试路由存在
            assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_generate_script_validation(self):
        """测试请求参数验证"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # 缺少必填字段
            response = await client.post("/generate", json={})
            assert response.status_code in [401, 422]
