"""
灵感模板+策略因子 - Service 测试
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.template.service import (
    create_factor,
    get_factors,
    get_factor_by_id,
    update_factor,
    delete_factor,
    increment_factor_usage,
    create_template,
    get_templates,
    get_template_by_id,
    update_template,
    delete_template,
    generate_script_from_template,
)
from app.template.schemas import (
    StrategyFactorCreate,
    StrategyFactorUpdate,
    InspirationTemplateCreate,
    InspirationTemplateUpdate,
    GenerateFromTemplateRequest,
)


@pytest.fixture
def mock_db():
    db = AsyncMock(spec=AsyncSession)
    return db


class TestStrategyFactorService:
    """策略因子Service测试"""

    @pytest.mark.asyncio
    async def test_create_factor(self, mock_db):
        """测试创建策略因子"""
        data = StrategyFactorCreate(
            name="夏天脱妆痛点开场",
            factor_type="hook",
            description="直击用户痛点",
            content={"text": "姐妹们，夏天是不是一出门就脱妆？"},
            category="美妆",
            tags=["痛点", "开场"],
        )

        factor = await create_factor(mock_db, "test_user", data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_factor_by_id_found(self, mock_db):
        """测试根据ID获取因子-找到"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = {"id": 1, "name": "测试因子"}
        mock_db.execute.return_value = mock_result

        factor = await get_factor_by_id(mock_db, 1, "test_user")

        assert factor is not None
        assert factor["id"] == 1

    @pytest.mark.asyncio
    async def test_get_factor_by_id_not_found(self, mock_db):
        """测试根据ID获取因子-未找到"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        factor = await get_factor_by_id(mock_db, 999, "test_user")

        assert factor is None

    @pytest.mark.asyncio
    async def test_update_factor_success(self, mock_db):
        """测试更新因子-成功"""
        with patch("app.template.service.get_factor_by_id", new_callable=AsyncMock) as mock_get:
            mock_factor = MagicMock()
            mock_get.return_value = mock_factor

            data = StrategyFactorUpdate(name="更新后的名称")
            result = await update_factor(mock_db, 1, "test_user", data)

            assert result is not None
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_factor_not_found(self, mock_db):
        """测试更新因子-未找到"""
        with patch("app.template.service.get_factor_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            data = StrategyFactorUpdate(name="更新后的名称")
            result = await update_factor(mock_db, 999, "test_user", data)

            assert result is None

    @pytest.mark.asyncio
    async def test_delete_factor_success(self, mock_db):
        """测试删除因子-成功"""
        with patch("app.template.service.get_factor_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"id": 1}

            result = await delete_factor(mock_db, 1, "test_user")

            assert result is True
            mock_db.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_factor_not_found(self, mock_db):
        """测试删除因子-未找到"""
        with patch("app.template.service.get_factor_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            result = await delete_factor(mock_db, 999, "test_user")

            assert result is False

    @pytest.mark.asyncio
    async def test_increment_factor_usage(self, mock_db):
        """测试增加因子使用次数"""
        with patch("app.template.service.get_factor_by_id", new_callable=AsyncMock) as mock_get:
            mock_factor = MagicMock()
            mock_factor.usage_count = 5
            mock_get.return_value = mock_factor

            await increment_factor_usage(mock_db, 1, "test_user")

            assert mock_factor.usage_count == 6
            mock_db.commit.assert_called_once()


class TestInspirationTemplateService:
    """灵感模板Service测试"""

    @pytest.mark.asyncio
    async def test_create_template(self, mock_db):
        """测试创建灵感模板"""
        data = InspirationTemplateCreate(
            name="痛点共鸣型带货模板",
            strategy="通过直击用户痛点引发共鸣",
            factors={"hook": "脱妆痛点开场", "cta": "限时优惠引导"},
            reference_video_ids=[1, 2, 3],
            category="美妆",
            tags=["带货", "痛点"],
        )

        template = await create_template(mock_db, "test_user", data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_template_by_id_found(self, mock_db):
        """测试根据ID获取模板-找到"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = {"id": 1, "name": "测试模板"}
        mock_db.execute.return_value = mock_result

        template = await get_template_by_id(mock_db, 1, "test_user")

        assert template is not None
        assert template["id"] == 1

    @pytest.mark.asyncio
    async def test_get_template_by_id_not_found(self, mock_db):
        """测试根据ID获取模板-未找到"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        template = await get_template_by_id(mock_db, 999, "test_user")

        assert template is None

    @pytest.mark.asyncio
    async def test_update_template_success(self, mock_db):
        """测试更新模板-成功"""
        with patch("app.template.service.get_template_by_id", new_callable=AsyncMock) as mock_get:
            mock_template = MagicMock()
            mock_get.return_value = mock_template

            data = InspirationTemplateUpdate(category="数码")
            result = await update_template(mock_db, 1, "test_user", data)

            assert result is not None
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_template_success(self, mock_db):
        """测试删除模板-成功"""
        with patch("app.template.service.get_template_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"id": 1}

            result = await delete_template(mock_db, 1, "test_user")

            assert result is True
            mock_db.delete.assert_called_once()


class TestGenerateScriptFromTemplate:
    """使用模板生成剧本测试"""

    @pytest.mark.asyncio
    async def test_generate_script_success(self, mock_db):
        """测试生成剧本-成功"""
        with patch("app.template.service.get_template_by_id", new_callable=AsyncMock) as mock_get_template:
            mock_template = MagicMock()
            mock_template.name = "测试模板"
            mock_template.category = "美妆"
            mock_template.strategy = "痛点共鸣策略"
            mock_template.factors = {"hook": "脱妆痛点开场"}
            mock_get_template.return_value = mock_template

            with patch("app.template.service.call_workflow", new_callable=AsyncMock) as mock_call:
                mock_call.return_value = {"scenes": [], "title": "生成的剧本"}

                request = GenerateFromTemplateRequest(
                    template_id=1,
                    product_info={"name": "粉底液", "price": "¥199"},
                )
                result = await generate_script_from_template(mock_db, "test_user", request)

                mock_call.assert_called_once()
                call_args = mock_call.call_args[0]
                assert call_args[0] == "script-generate"
                assert "product_info" in call_args[1]
                assert call_args[1]["product_info"]["name"] == "粉底液"

    @pytest.mark.asyncio
    async def test_generate_script_template_not_found(self, mock_db):
        """测试生成剧本-模板不存在"""
        with patch("app.template.service.get_template_by_id", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            request = GenerateFromTemplateRequest(template_id=999)

            with pytest.raises(ValueError, match="模板不存在"):
                await generate_script_from_template(mock_db, "test_user", request)

    @pytest.mark.asyncio
    async def test_generate_script_with_custom_factors(self, mock_db):
        """测试生成剧本-带自定义因子"""
        with patch("app.template.service.get_template_by_id", new_callable=AsyncMock) as mock_get_template:
            mock_template = MagicMock()
            mock_template.name = "测试模板"
            mock_template.strategy = "测试策略"
            mock_template.factors = {"hook": "默认因子"}
            mock_get_template.return_value = mock_template

            with patch("app.template.service.get_factor_by_id", new_callable=AsyncMock) as mock_get_factor:
                mock_factor = MagicMock()
                mock_factor.content = {"text": "自定义因子内容"}
                mock_get_factor.return_value = mock_factor

                with patch("app.template.service.call_workflow", new_callable=AsyncMock) as mock_call:
                    mock_call.return_value = {"scenes": []}

                    request = GenerateFromTemplateRequest(
                        template_id=1,
                        custom_factors={"hook": 5},
                    )
                    result = await generate_script_from_template(mock_db, "test_user", request)

                    mock_call.assert_called_once()
                    call_args = mock_call.call_args[0]
                    assert call_args[1]["factors"]["hook"]["text"] == "自定义因子内容"
