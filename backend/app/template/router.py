"""
灵感模板+策略因子 - API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from .schemas import (
    StrategyFactorCreate,
    StrategyFactorUpdate,
    StrategyFactorResponse,
    FactorListResponse,
    InspirationTemplateCreate,
    InspirationTemplateUpdate,
    InspirationTemplateResponse,
    TemplateListResponse,
    GenerateFromTemplateRequest,
)
from .service import (
    create_factor,
    get_factors,
    get_factor_by_id,
    update_factor,
    delete_factor,
    create_template,
    get_templates,
    get_template_by_id,
    update_template,
    delete_template,
    generate_script_from_template,
    DEFAULT_USER_ID,
)

router = APIRouter(prefix="/api/v1/template", tags=["template"])


# ── Strategy Factor Routes ─────────────────

@router.post("/factors", response_model=StrategyFactorResponse)
async def create_factor_endpoint(
    data: StrategyFactorCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建策略因子"""
    return await create_factor(db, DEFAULT_USER_ID, data)


@router.get("/factors", response_model=FactorListResponse)
async def list_factors(
    factor_type: Optional[str] = Query(None, description="按因子类型筛选：hook / scene / narration / visual / ending"),
    category: Optional[str] = Query(None, description="按分类筛选"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取策略因子列表"""
    total, factors = await get_factors(db, DEFAULT_USER_ID, factor_type, category, skip, limit)
    return FactorListResponse(total=total, items=factors)


@router.get("/factors/{factor_id}", response_model=StrategyFactorResponse)
async def get_factor(
    factor_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取策略因子详情"""
    factor = await get_factor_by_id(db, factor_id, DEFAULT_USER_ID)
    if not factor:
        raise HTTPException(status_code=404, detail="因子不存在")
    return factor


@router.put("/factors/{factor_id}", response_model=StrategyFactorResponse)
async def update_factor_endpoint(
    factor_id: int,
    data: StrategyFactorUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新策略因子"""
    factor = await update_factor(db, factor_id, DEFAULT_USER_ID, data)
    if not factor:
        raise HTTPException(status_code=404, detail="因子不存在")
    return factor


@router.delete("/factors/{factor_id}")
async def delete_factor_endpoint(
    factor_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除策略因子"""
    success = await delete_factor(db, factor_id, DEFAULT_USER_ID)
    if not success:
        raise HTTPException(status_code=404, detail="因子不存在")
    return {"success": True, "message": "删除成功"}


# ── Inspiration Template Routes ─────────────────

@router.post("/templates", response_model=InspirationTemplateResponse)
async def create_template_endpoint(
    data: InspirationTemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建灵感模板"""
    return await create_template(db, DEFAULT_USER_ID, data)


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    category: Optional[str] = Query(None, description="按分类筛选"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取灵感模板列表"""
    total, templates = await get_templates(db, DEFAULT_USER_ID, category, skip, limit)
    return TemplateListResponse(total=total, items=templates)


@router.get("/templates/{template_id}", response_model=InspirationTemplateResponse)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取灵感模板详情"""
    template = await get_template_by_id(db, template_id, DEFAULT_USER_ID)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return template


@router.put("/templates/{template_id}", response_model=InspirationTemplateResponse)
async def update_template_endpoint(
    template_id: int,
    data: InspirationTemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新灵感模板"""
    template = await update_template(db, template_id, DEFAULT_USER_ID, data)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return template


@router.delete("/templates/{template_id}")
async def delete_template_endpoint(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除灵感模板"""
    success = await delete_template(db, template_id, DEFAULT_USER_ID)
    if not success:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"success": True, "message": "删除成功"}


# ── Generate Script from Template ─────────────────

@router.post("/templates/{template_id}/generate-script")
async def generate_script(
    template_id: int,
    request: GenerateFromTemplateRequest,
    db: AsyncSession = Depends(get_db),
):
    """使用模板生成剧本"""
    try:
        result = await generate_script_from_template(db, DEFAULT_USER_ID, request)
        return {
            "success": True,
            "template_id": template_id,
            "script": result,
            "message": "剧本生成成功"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")
