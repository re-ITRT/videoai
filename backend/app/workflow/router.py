"""工作流配置路由"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_user
from app.auth.models import User
from app.workflow.models import (
    WorkflowConfig, WorkflowConfigResponse, WorkflowConfigUpdate,
    AVAILABLE_WORKFLOWS,
)
import os

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


async def get_or_create_config(db: AsyncSession, user_id: int, workflow_name: str) -> WorkflowConfig:
    result = await db.execute(
        select(WorkflowConfig).where(
            WorkflowConfig.user_id == user_id,
            WorkflowConfig.workflow_name == workflow_name,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        config = WorkflowConfig(user_id=user_id, workflow_name=workflow_name, config="{}")
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config


@router.get("/available")
async def list_available_workflows():
    """列出可用的本地工作流"""
    return {"workflows": AVAILABLE_WORKFLOWS}


@router.get("/configs", response_model=list[WorkflowConfigResponse])
async def list_workflow_configs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出用户的所有工作流配置"""
    result = await db.execute(
        select(WorkflowConfig).where(WorkflowConfig.user_id == current_user.id)
    )
    configs = result.scalars().all()
    return [
        WorkflowConfigResponse(
            workflow_name=c.workflow_name,
            config=json.loads(c.config or "{}"),
            enabled=bool(c.enabled),
        )
        for c in configs
    ]


@router.get("/configs/{workflow_name}", response_model=WorkflowConfigResponse)
async def get_workflow_config(
    workflow_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个工作流配置"""
    config = await get_or_create_config(db, current_user.id, workflow_name)
    return WorkflowConfigResponse(
        workflow_name=config.workflow_name,
        config=json.loads(config.config or "{}"),
        enabled=bool(config.enabled),
    )


@router.put("/configs/{workflow_name}", response_model=WorkflowConfigResponse)
async def update_workflow_config(
    workflow_name: str,
    update: WorkflowConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新工作流配置"""
    config = await get_or_create_config(db, current_user.id, workflow_name)
    if update.config is not None:
        config.config = json.dumps(update.config)
    if update.enabled is not None:
        config.enabled = 1 if update.enabled else 0
    await db.commit()
    await db.refresh(config)
    return WorkflowConfigResponse(
        workflow_name=config.workflow_name,
        config=json.loads(config.config or "{}"),
        enabled=bool(config.enabled),
    )


PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")


@router.get("/prompts/{workflow_name}")
async def get_workflow_prompts(workflow_name: str):
    """读取工作流的 prompt 文件"""
    wf_dir = os.path.join(PROMPT_DIR, workflow_name)
    if not os.path.isdir(wf_dir):
        return {"files": {}}
    files = {}
    for fname in os.listdir(wf_dir):
        fpath = os.path.join(wf_dir, fname)
        if os.path.isfile(fpath) and fname.endswith((".md", ".j2")):
            with open(fpath, "r", encoding="utf-8") as f:
                files[fname] = f.read()
    return {"files": files}


@router.put("/prompts/{workflow_name}/{filename}")
async def update_workflow_prompt(workflow_name: str, filename: str, body: dict):
    """更新工作流的 prompt 文件"""
    if not filename.endswith((".md", ".j2")):
        raise HTTPException(status_code=400, detail="只支持 .md 和 .j2 文件")
    fpath = os.path.join(PROMPT_DIR, workflow_name, filename)
    content = body.get("content", "")
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    return {"ok": True}
