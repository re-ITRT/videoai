"""material/search.py全覆盖测试"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


class TestSearchMaterials:
    @pytest.mark.asyncio
    async def test_workflow_returns_no_embeddings(self, db_session):
        from app.material.search import search_materials
        with patch("app.material.search.call_workflow", new_callable=AsyncMock) as cwf:
            cwf.return_value = {"product_embeddings": []}
            result = await search_materials(db_session, "user1", "test query")
            assert result == []

    @pytest.mark.asyncio
    async def test_workflow_raises_exception(self, db_session):
        from app.material.search import search_materials
        with patch("app.material.search.call_workflow", new_callable=AsyncMock,
                   side_effect=Exception("workflow failed")):
            result = await search_materials(db_session, "user1", "test query")
            assert result == []

    @pytest.mark.asyncio
    async def test_empty_embedding_vector_skipped(self, db_session):
        from app.material.search import search_materials
        with patch("app.material.search.call_workflow", new_callable=AsyncMock) as cwf:
            cwf.return_value = {"product_embeddings": [{"embedding": []}, {"embedding": [0.1, 0.2]}]}
            with patch("sqlalchemy.ext.asyncio.AsyncSession.execute", new_callable=AsyncMock) as ex:
                # pgvector <-> 操作符在 SQLite 中不支持，mock 返回值
                mock_result = MagicMock()
                mock_result.mappings.return_value.all.return_value = [
                    {"id": 1, "similarity": 0.85, "image_url": "/u/1.jpg"}
                ]
                ex.return_value = mock_result
                result = await search_materials(db_session, "user1", "test query")
                assert len(result) == 1

    @pytest.mark.asyncio
    async def test_slice_search_level(self, db_session):
        from app.material.search import search_materials
        with patch("app.material.search.call_workflow", new_callable=AsyncMock) as cwf:
            cwf.return_value = {"product_embeddings": [{"embedding": [0.1, 0.2]}]}
            with patch("sqlalchemy.ext.asyncio.AsyncSession.execute", new_callable=AsyncMock) as ex:
                mock_result = MagicMock()
                mock_result.mappings.return_value.all.return_value = [
                    {"id": 10, "material_id": 1, "similarity": 0.9}
                ]
                ex.return_value = mock_result
                result = await search_materials(
                    db_session, "user1", "test query", search_level="slice"
                )
                assert len(result) == 1

    @pytest.mark.asyncio
    async def test_sql_execution_error_skipped(self, db_session):
        from app.material.search import search_materials
        with patch("app.material.search.call_workflow", new_callable=AsyncMock) as cwf:
            cwf.return_value = {"product_embeddings": [{"embedding": [0.1, 0.2]}]}
            with patch("sqlalchemy.ext.asyncio.AsyncSession.execute", new_callable=AsyncMock,
                       side_effect=Exception("pgvector error")):
                result = await search_materials(db_session, "user1", "test query")
                assert result == []

    @pytest.mark.asyncio
    async def test_dedup_same_id(self, db_session):
        from app.material.search import search_materials
        with patch("app.material.search.call_workflow", new_callable=AsyncMock) as cwf:
            cwf.return_value = {"product_embeddings": [
                {"embedding": [0.1]}, {"embedding": [0.2]}
            ]}
            with patch("sqlalchemy.ext.asyncio.AsyncSession.execute", new_callable=AsyncMock) as ex:
                mock_result = MagicMock()
                mock_result.mappings.return_value.all.side_effect = [
                    [{"id": 1, "similarity": 0.85}],
                    [{"id": 1, "similarity": 0.90}],
                ]
                ex.return_value = mock_result
                result = await search_materials(db_session, "user1", "test query")
                assert len(result) == 1  # dedup

    @pytest.mark.asyncio
    async def test_search_by_embeddings(self, db_session):
        from app.material.search import search_materials_by_embeddings
        with patch("sqlalchemy.ext.asyncio.AsyncSession.execute", new_callable=AsyncMock) as ex:
            mock_result = MagicMock()
            mock_result.mappings.return_value.all.return_value = [
                {"id": 5, "similarity": 0.95, "image_url": "/u/5.jpg"}
            ]
            ex.return_value = mock_result
            result = await search_materials_by_embeddings(
                db_session, "user1", [0.1, 0.2, 0.3], threshold=0.5
            )
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_fallback(self, db_session):
        from app.material.search import search_materials_fallback
        with patch("sqlalchemy.ext.asyncio.AsyncSession.execute", new_callable=AsyncMock) as ex:
            mock_result = MagicMock()
            mock_result.mappings.return_value.all.return_value = [
                {"id": 3, "similarity": 1.0, "image_url": "/u/3.jpg"}
            ]
            ex.return_value = mock_result
            result = await search_materials_fallback(
                db_session, "user1", "test", max_results=10
            )
            assert len(result) == 1
