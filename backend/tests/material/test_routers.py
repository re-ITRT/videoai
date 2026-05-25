"""素材模块测试 — B 负责"""
import pytest


class TestMaterialRoutes:
    """验证路由存在性（stub 阶段）"""

    @pytest.mark.asyncio
    async def test_upload_material(self, client):
        """POST /api/v1/materials/upload"""
        resp = await client.post("/api/v1/materials/upload", json={
            "material_type": "product",
            "input_type": "image",
        })
        # 路由注册正常即可（实现后改为 200 + 具体 body）
        assert resp.status_code in (200, 422, 401)

    @pytest.mark.asyncio
    async def test_list_materials(self, client):
        """GET /api/v1/materials"""
        resp = await client.get("/api/v1/materials")
        assert resp.status_code in (200, 401)

    @pytest.mark.asyncio
    async def test_search_materials(self, client):
        """POST /api/v1/materials/search"""
        resp = await client.post("/api/v1/materials/search", json={
            "query": "test",
            "threshold": 0.6,
        })
        assert resp.status_code in (200, 422, 401)

    @pytest.mark.asyncio
    async def test_delete_material(self, client):
        """DELETE /api/v1/materials/{id}"""
        resp = await client.delete("/api/v1/materials/1")
        assert resp.status_code in (200, 204, 401, 404)

    @pytest.mark.asyncio
    async def test_material_slice_crud(self, client):
        """素材切片相关端点"""
        # upload → slice → list → delete
        assert True  # placeholder


class TestMaterialSchemas:
    """验证 Pydantic schema 行为"""

    def test_upload_request_valid(self):
        from app.material.schemas import MaterialUploadRequest
        req = MaterialUploadRequest(material_type="product", input_type="image")
        assert req.material_type == "product"
        assert req.input_type == "image"
        assert req.product_id is None

    def test_search_request_defaults(self):
        from app.material.schemas import MaterialSearchRequest
        req = MaterialSearchRequest(query="watch")
        assert req.query == "watch"
        assert req.threshold == 0.6
        assert req.max_results == 50
        assert req.search_level == "material"
