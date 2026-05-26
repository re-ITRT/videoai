"""
灵感模板+策略因子 - 业务逻辑
"""
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.script.models import InspirationTemplate, StrategyFactor
from app.workers.workflow import call_workflow
from .schemas import (
    InspirationTemplateCreate,
    InspirationTemplateUpdate,
    StrategyFactorCreate,
    StrategyFactorUpdate,
    GenerateFromTemplateRequest,
)

DEFAULT_USER_ID = "dev_user"


# ── Strategy Factor CRUD ─────────────────

async def create_factor(
    db: AsyncSession,
    user_id: str,
    data: StrategyFactorCreate,
) -> StrategyFactor:
    """创建策略因子"""
    factor = StrategyFactor(
        user_id=user_id,
        name=data.name,
        factor_type=data.factor_type,
        description=data.description,
        content=data.content,
        category=data.category,
        tags=data.tags,
    )
    db.add(factor)
    await db.commit()
    await db.refresh(factor)
    return factor


async def get_factors(
    db: AsyncSession,
    user_id: str,
    factor_type: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
) -> Tuple[int, List[StrategyFactor]]:
    """获取策略因子列表"""
    query = select(StrategyFactor).where(StrategyFactor.user_id == user_id)

    if factor_type:
        query = query.where(StrategyFactor.factor_type == factor_type)
    if category:
        query = query.where(StrategyFactor.category == category)

    # 总数
    count_query = select(func.count(StrategyFactor.id)).where(StrategyFactor.user_id == user_id)
    if factor_type:
        count_query = count_query.where(StrategyFactor.factor_type == factor_type)
    if category:
        count_query = count_query.where(StrategyFactor.category == category)

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # 列表
    query = query.order_by(desc(StrategyFactor.usage_count), desc(StrategyFactor.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    factors = result.scalars().all()

    return total, list(factors)


async def get_factor_by_id(
    db: AsyncSession,
    factor_id: int,
    user_id: str,
) -> Optional[StrategyFactor]:
    """根据ID获取策略因子"""
    query = select(StrategyFactor).where(
        StrategyFactor.id == factor_id,
        StrategyFactor.user_id == user_id,
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def update_factor(
    db: AsyncSession,
    factor_id: int,
    user_id: str,
    data: StrategyFactorUpdate,
) -> Optional[StrategyFactor]:
    """更新策略因子"""
    factor = await get_factor_by_id(db, factor_id, user_id)
    if not factor:
        return None

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(factor, field, value)

    await db.commit()
    await db.refresh(factor)
    return factor


async def delete_factor(
    db: AsyncSession,
    factor_id: int,
    user_id: str,
) -> bool:
    """删除策略因子"""
    factor = await get_factor_by_id(db, factor_id, user_id)
    if not factor:
        return False

    await db.delete(factor)
    await db.commit()
    return True


async def increment_factor_usage(
    db: AsyncSession,
    factor_id: int,
    user_id: str,
):
    """增加因子使用次数"""
    factor = await get_factor_by_id(db, factor_id, user_id)
    if factor:
        factor.usage_count += 1
        await db.commit()


# ── Inspiration Template CRUD ─────────────────

async def create_template(
    db: AsyncSession,
    user_id: str,
    data: InspirationTemplateCreate,
) -> InspirationTemplate:
    """创建灵感模板"""
    template = InspirationTemplate(
        user_id=user_id,
        name=data.name,
        strategy=data.strategy,
        factors=data.factors,
        reference_video_ids=data.reference_video_ids,
        category=data.category,
        tags=data.tags,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


async def get_templates(
    db: AsyncSession,
    user_id: str,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
) -> Tuple[int, List[InspirationTemplate]]:
    """获取灵感模板列表"""
    query = select(InspirationTemplate).where(InspirationTemplate.user_id == user_id)

    if category:
        query = query.where(InspirationTemplate.category == category)

    # 总数
    count_query = select(func.count(InspirationTemplate.id)).where(InspirationTemplate.user_id == user_id)
    if category:
        count_query = count_query.where(InspirationTemplate.category == category)

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # 列表
    query = query.order_by(desc(InspirationTemplate.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    templates = result.scalars().all()

    return total, list(templates)


async def get_template_by_id(
    db: AsyncSession,
    template_id: int,
    user_id: str,
) -> Optional[InspirationTemplate]:
    """根据ID获取灵感模板"""
    query = select(InspirationTemplate).where(
        InspirationTemplate.id == template_id,
        InspirationTemplate.user_id == user_id,
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def update_template(
    db: AsyncSession,
    template_id: int,
    user_id: str,
    data: InspirationTemplateUpdate,
) -> Optional[InspirationTemplate]:
    """更新灵感模板"""
    template = await get_template_by_id(db, template_id, user_id)
    if not template:
        return None

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)
    return template


async def delete_template(
    db: AsyncSession,
    template_id: int,
    user_id: str,
) -> bool:
    """删除灵感模板"""
    template = await get_template_by_id(db, template_id, user_id)
    if not template:
        return False

    await db.delete(template)
    await db.commit()
    return True


# ── Generate Script from Template ─────────────────

async def generate_script_from_template(
    db: AsyncSession,
    user_id: str,
    request: GenerateFromTemplateRequest,
) -> Dict[str, Any]:
    """使用模板生成剧本"""
    template = await get_template_by_id(db, request.template_id, user_id)
    if not template:
        raise ValueError(f"模板不存在: {request.template_id}")

    # 1. 获取模板中的因子
    template_factors = template.factors or {}

    # 2. 如果有自定义因子覆盖，使用自定义的
    if request.custom_factors:
        for step, factor_id in request.custom_factors.items():
            factor = await get_factor_by_id(db, factor_id, user_id)
            if factor:
                template_factors[step] = factor.content
                await increment_factor_usage(db, factor_id, user_id)

    # 3. 构建工作流请求
    payload = {
        "strategy": template.strategy,
        "factors": template_factors,
        "product_info": request.product_info or {},
        "template_name": template.name,
        "template_category": template.category,
    }

    # 4. 调用 script-generate 工作流
    result = await call_workflow("script-generate", payload)

    return result
