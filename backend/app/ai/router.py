"""AI Agent 配置路由"""
import json
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_user
from app.auth.models import User
from app.ai.models import UserAIConfig, AIConfigResponse, AIConfigUpdate

from pydantic import BaseModel


class ScanModelsRequest(BaseModel):
    base_url: str | None = None
    api_key: str | None = None


router = APIRouter(prefix="/api/v1/users/me/ai-config", tags=["ai"])


async def get_or_create_config(db: AsyncSession, user_id: int) -> UserAIConfig:
    result = await db.execute(select(UserAIConfig).where(UserAIConfig.user_id == user_id))
    config = result.scalar_one_or_none()
    if not config:
        config = UserAIConfig(user_id=user_id, api_key="", base_url="https://api.openai.com/v1", model="gpt-4o")
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config


@router.get("", response_model=AIConfigResponse)
async def get_ai_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户AI配置"""
    config = await get_or_create_config(db, current_user.id)
    models = json.loads(config.available_models or "[]")
    return AIConfigResponse(
        base_url=config.base_url,
        model=config.model,
        available_models=models,
    )


@router.put("", response_model=AIConfigResponse)
async def update_ai_config(
    update: AIConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新用户AI配置"""
    config = await get_or_create_config(db, current_user.id)
    if update.base_url is not None:
        config.base_url = update.base_url
    if update.api_key is not None:
        config.api_key = update.api_key
    if update.model is not None:
        config.model = update.model
    await db.commit()
    await db.refresh(config)
    models = json.loads(config.available_models or "[]")
    return AIConfigResponse(
        base_url=config.base_url,
        model=config.model,
        available_models=models,
    )


@router.post("/scan-models")
async def scan_available_models(
    body: ScanModelsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """扫描可用模型列表"""
    config = await get_or_create_config(db, current_user.id)
    url = (body.base_url or config.base_url).rstrip("/") + "/models"
    key = body.api_key or config.api_key

    if not key:
        raise HTTPException(status_code=400, detail="请先配置 API Key")

    headers = {"Authorization": f"Bearer {key}"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            models = [m["id"] for m in data.get("data", []) if "id" in m]
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"API 返回错误: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"连接失败: {str(e)}")

    config.available_models = json.dumps(models)
    if body.base_url:
        config.base_url = body.base_url
    if body.api_key:
        config.api_key = body.api_key
    await db.commit()

    return {"models": models, "selected": config.model}
