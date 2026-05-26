"""素材检索服务测试 — M6/M7"""
import pytest
from unittest.mock import AsyncMock


async def _mock_workflow(name, payload):
    return {"product_embeddings": []}


class TestSearchService:

    @pytest.mark.asyncio
    async def test_search_empty_embeddings(self, db_session):
        """无 embedding → 空结果"""
        from app.material.search import search_materials

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.material.search.call_workflow", _mock_workflow)
            results = await search_materials(db_session, "user1", "test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_workflow_failure(self, db_session):
        """工作流失败 → 不报错，返回空"""
        from app.material.search import search_materials

        async def fail_workflow(name, payload):
            raise Exception("网络错误")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.material.search.call_workflow", fail_workflow)
            results = await search_materials(db_session, "user1", "test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_with_embeddings(self, db_session):
        """有 embedding 时尝试 pgvector 查询"""
        from app.material.search import search_materials

        async def mock_wf(name, payload):
            return {
                "product_embeddings": [
                    {"query": "test", "embedding": [0.1] * 1024, "embedding_dim": 1024}
                ]
            }

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.material.search.call_workflow", mock_wf)
            results = await search_materials(db_session, "user1", "test")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_fallback_text(self, db_session):
        """文本回退搜索"""
        from app.material.search import search_materials_fallback
        from app.material.models import Material

        db_session.add(Material(user_id="user1", material_type="product",
                                 input_type="image", text_content="智能手表测试"))
        await db_session.commit()

        results = await search_materials_fallback(db_session, "user1", "智能")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_fallback_no_match(self, db_session):
        from app.material.search import search_materials_fallback
        results = await search_materials_fallback(db_session, "user1", "zzzzz_notfound")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_fallback_max_results(self, db_session):
        from app.material.search import search_materials_fallback
        from app.material.models import Material

        for i in range(5):
            db_session.add(Material(user_id="user1", material_type="product",
                                     input_type="image", text_content=f"测试内容{i}"))
        await db_session.commit()

        results = await search_materials_fallback(db_session, "user1", "测试", max_results=2)
        assert len(results) <= 2


class TestSearchRouterDirect:

    @pytest.mark.asyncio
    async def test_search_direct_empty(self, db_session, dummy_user):
        from app.material.router import search_materials
        from app.material.schemas import MaterialSearchRequest

        async def mock_wf(name, payload):
            return {"product_embeddings": []}

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.material.search.call_workflow", mock_wf)
            results = await search_materials(
                request=MaterialSearchRequest(query="test"),
                db=db_session, current_user=dummy_user,
            )
        assert results == []
