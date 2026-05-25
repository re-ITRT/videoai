"""素材模块测试 — B 负责"""
import pytest


async def _register(client, username):
    resp = await client.post("/api/v1/auth/register", json={
        "username": username, "password": "Test12345"
    })
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _register_and_upload_video(client, username):
    headers = await _register(client, username)
    upload = await client.post("/api/v1/materials/upload", json={
        "material_type": "product", "input_type": "video"
    }, headers=headers)
    return headers, upload.json()["id"]


class TestMaterialRoutes:
    """素材 CRUD"""

    @pytest.mark.asyncio
    async def test_upload_material(self, client):
        headers = await _register(client, "uploader1")
        resp = await client.post("/api/v1/materials/upload", json={
            "material_type": "product", "input_type": "image",
            "image_url": "https://example.com/img.jpg",
        }, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["material_type"] == "product"
        assert resp.json()["id"] > 0

    @pytest.mark.asyncio
    async def test_upload_video_creates_slices(self, client):
        headers = await _register(client, "video_up")
        resp = await client.post("/api/v1/materials/upload", json={
            "material_type": "product", "input_type": "video",
        }, headers=headers)
        assert resp.status_code == 200
        mid = resp.json()["id"]

        resp = await client.get(f"/api/v1/materials/{mid}/slices", headers=headers)
        assert resp.status_code == 200
        slices = resp.json()
        assert len(slices) == 3
        assert slices[0]["slice_type"] == "video_scene"

    @pytest.mark.asyncio
    async def test_list_materials(self, client):
        headers = await _register(client, "list_u1")
        resp = await client.get("/api/v1/materials", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_get_material_detail(self, client):
        headers = await _register(client, "detail_u")
        upload = await client.post("/api/v1/materials/upload", json={
            "material_type": "product", "input_type": "image"
        }, headers=headers)
        mid = upload.json()["id"]
        resp = await client.get(f"/api/v1/materials/{mid}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == mid

    @pytest.mark.asyncio
    async def test_get_nonexistent_material(self, client):
        headers = await _register(client, "notfound")
        resp = await client.get("/api/v1/materials/99999", headers=headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_material(self, client):
        headers = await _register(client, "del_u1")
        upload = await client.post("/api/v1/materials/upload", json={
            "material_type": "product", "input_type": "image"
        }, headers=headers)
        mid = upload.json()["id"]
        resp = await client.delete(f"/api/v1/materials/{mid}", headers=headers)
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_search_materials(self, client):
        headers = await _register(client, "search_u")
        resp = await client.post("/api/v1/materials/search", json={
            "query": "test", "threshold": 0.6
        }, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_upload_no_auth(self, client):
        resp = await client.post("/api/v1/materials/upload", json={
            "material_type": "product", "input_type": "image"
        })
        assert resp.status_code == 403


class TestSliceRoutes:
    """M4 素材切片"""

    @pytest.mark.asyncio
    async def test_list_slices(self, client):
        headers, mid = await _register_and_upload_video(client, "sl1")
        resp = await client.get(f"/api/v1/materials/{mid}/slices", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    @pytest.mark.asyncio
    async def test_list_slices_filter(self, client):
        headers, mid = await _register_and_upload_video(client, "sl2")
        resp = await client.get(
            f"/api/v1/materials/{mid}/slices?slice_type=video_scene",
            headers=headers,
        )
        assert resp.status_code == 200
        assert all(s["slice_type"] == "video_scene" for s in resp.json())

    @pytest.mark.asyncio
    async def test_create_slice(self, client):
        headers, mid = await _register_and_upload_video(client, "sl3")
        resp = await client.post(
            f"/api/v1/materials/{mid}/slices",
            json={"slice_type": "video_scene", "scene_id": 99, "description": "自定义"},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["scene_id"] == 99

    @pytest.mark.asyncio
    async def test_slices_nonexistent(self, client):
        headers = await _register(client, "nosl")
        resp = await client.get("/api/v1/materials/99999/slices", headers=headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_slice_nonexistent(self, client):
        headers = await _register(client, "csl404")
        resp = await client.post(
            "/api/v1/materials/99999/slices",
            json={"slice_type": "video_scene"},
            headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_slices_no_auth(self, client):
        resp = await client.get("/api/v1/materials/1/slices")
        assert resp.status_code == 403


class TestMaterialSchemas:

    def test_upload_request(self):
        from app.material.schemas import MaterialUploadRequest
        req = MaterialUploadRequest(material_type="product", input_type="image")
        assert req.input_type == "image"

    def test_search_request_defaults(self):
        from app.material.schemas import MaterialSearchRequest
        req = MaterialSearchRequest(query="watch")
        assert req.threshold == 0.6
        assert req.search_level == "material"

    def test_slice_create_request(self):
        from app.material.schemas import SliceCreateRequest
        req = SliceCreateRequest(slice_type="video_scene", scene_id=1)
        assert req.scene_id == 1

    def test_slice_response(self):
        from app.material.schemas import SliceResponse
        r = SliceResponse(id=1, material_id=10, slice_type="keyframe", time_range="0-5s")
        assert r.time_range == "0-5s"
