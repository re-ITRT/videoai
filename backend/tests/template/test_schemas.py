"""
灵感模板+策略因子 - Schemas 测试
"""
import pytest
import json
from app.template.schemas import (
    StrategyFactorCreate,
    StrategyFactorUpdate,
    InspirationTemplateCreate,
    InspirationTemplateUpdate,
    GenerateFromTemplateRequest,
)


class TestStrategyFactorSchemas:
    """策略因子Schema测试"""

    def test_create_factor_valid(self):
        """测试创建因子-有效数据"""
        data = {
            "name": "夏天脱妆痛点开场",
            "factor_type": "hook",
            "description": "直击用户夏天脱妆的痛点",
            "content": {"text": "姐妹们，夏天是不是一出门就脱妆？", "duration": "3s"},
            "category": "美妆",
            "tags": ["痛点", "开场"],
        }
        factor = StrategyFactorCreate(**data)
        assert factor.name == data["name"]
        assert factor.factor_type == "hook"
        assert factor.content["text"] == "姐妹们，夏天是不是一出门就脱妆？"

    def test_create_factor_minimal(self):
        """测试创建因子-最小数据"""
        data = {
            "name": "产品特写",
            "factor_type": "visual",
            "content": {"visual": "产品360度旋转展示"},
        }
        factor = StrategyFactorCreate(**data)
        assert factor.name == "产品特写"
        assert factor.category is None
        assert factor.tags == []

    def test_update_factor_partial(self):
        """测试更新因子-部分字段"""
        data = {"name": "更新后的名称", "tags": ["新标签"]}
        update = StrategyFactorUpdate(**data)
        assert update.name == "更新后的名称"
        assert update.factor_type is None
        assert update.content is None


class TestInspirationTemplateSchemas:
    """灵感模板Schema测试"""

    def test_create_template_valid(self):
        """测试创建模板-有效数据"""
        data = {
            "name": "痛点共鸣型带货模板",
            "strategy": "通过直击用户痛点引发共鸣，快速展示产品核心价值，最后用优惠活动引导下单",
            "factors": {
                "hook": "脱妆痛点开场",
                "product_show": "产品特写展示",
                "cta": "限时优惠引导",
            },
            "reference_video_ids": [1, 2, 3],
            "category": "美妆",
            "tags": ["带货", "痛点", "美妆"],
        }
        template = InspirationTemplateCreate(**data)
        assert template.name == data["name"]
        assert template.factors["hook"] == "脱妆痛点开场"
        assert len(template.reference_video_ids) == 3

    def test_create_template_minimal(self):
        """测试创建模板-最小数据"""
        data = {
            "name": "简单模板",
            "strategy": "简单直接展示产品",
        }
        template = InspirationTemplateCreate(**data)
        assert template.name == "简单模板"
        assert template.factors == {}
        assert template.reference_video_ids == []
        assert template.category is None

    def test_update_template_partial(self):
        """测试更新模板-部分字段"""
        data = {"category": "数码", "tags": ["科技", "新品"]}
        update = InspirationTemplateUpdate(**data)
        assert update.category == "数码"
        assert update.name is None
        assert update.strategy is None


class TestGenerateFromTemplateSchemas:
    """从模板生成剧本Schema测试"""

    def test_generate_request_basic(self):
        """测试生成请求-基本数据"""
        data = {"template_id": 1}
        request = GenerateFromTemplateRequest(**data)
        assert request.template_id == 1
        assert request.product_info is None
        assert request.custom_factors is None

    def test_generate_request_with_product_info(self):
        """测试生成请求-带产品信息"""
        data = {
            "template_id": 1,
            "product_info": {
                "name": "持妆粉底液",
                "price": "¥199",
                "features": ["持妆24小时", "防水防汗"],
            },
        }
        request = GenerateFromTemplateRequest(**data)
        assert request.template_id == 1
        assert request.product_info["name"] == "持妆粉底液"
        assert len(request.product_info["features"]) == 2

    def test_generate_request_with_custom_factors(self):
        """测试生成请求-带自定义因子"""
        data = {
            "template_id": 1,
            "custom_factors": {"hook": 5, "scene1": 8, "cta": 10},
        }
        request = GenerateFromTemplateRequest(**data)
        assert request.custom_factors["hook"] == 5
        assert request.custom_factors["scene1"] == 8
