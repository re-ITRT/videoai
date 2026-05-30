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
import os, httpx, shutil

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
TEMPLATES_DIR = os.path.join(PROMPT_DIR, "templates")


@router.get("/prompts")
async def list_all_templates():
    """列出所有模板（含名称/描述/prompt预览）"""
    if not os.path.isdir(TEMPLATES_DIR):
        return {"templates": {}}
    result = {}
    for tname in sorted(os.listdir(TEMPLATES_DIR)):
        tdir = os.path.join(TEMPLATES_DIR, tname)
        if not os.path.isdir(tdir):
            continue
        info = {}
        info_path = os.path.join(tdir, "template_info.json")
        if os.path.exists(info_path):
            with open(info_path, "r", encoding="utf-8") as f:
                info = json.loads(f.read())
        sp = os.path.join(tdir, "system.md")
        preview = ""
        if os.path.exists(sp):
            with open(sp, "r", encoding="utf-8") as f:
                preview = f.read()[:200]
        result[tname] = {
            "display_name": info.get("name", tname),
            "description": info.get("description", ""),
            "tags": info.get("tags", []),
            "prompt_preview": preview,
        }
    return {"templates": result}


@router.get("/prompts/output-format")
async def get_output_format():
    """获取输出格式定义（只读，不包含在模板中）"""
    fpath = os.path.join(PROMPT_DIR, "output_format.md")
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            return {"content": f.read()}
    return {"content": ""}


@router.get("/prompts/{workflow_name}")
async def get_workflow_prompts(workflow_name: str):
    """读取工作流或模板的 prompt 文件"""
    # 先查 templates 目录，再查 prompts 根目录
    for base in [TEMPLATES_DIR, PROMPT_DIR]:
        wf_dir = os.path.join(base, workflow_name)
        if os.path.isdir(wf_dir):
            break
    else:
        return {"files": {}}
    files = {}
    for fname in os.listdir(wf_dir):
        fpath = os.path.join(wf_dir, fname)
        if os.path.isfile(fpath) and fname.endswith((".md", ".j2", ".json")):
            with open(fpath, "r", encoding="utf-8") as f:
                files[fname] = f.read()
    return {"files": files}


@router.put("/prompts/{workflow_name}/{filename}")
async def update_workflow_prompt(workflow_name: str, filename: str, body: dict):
    """更新工作流或模板的 prompt 文件"""
    if not filename.endswith((".md", ".j2", ".json")):
        raise HTTPException(status_code=400, detail="不支持的文件类型")
    # 优先 templates 目录
    for base in [TEMPLATES_DIR, PROMPT_DIR]:
        fpath = os.path.join(base, workflow_name, filename)
        if os.path.exists(fpath) or base == TEMPLATES_DIR:
            break
    else:
        fpath = os.path.join(TEMPLATES_DIR, workflow_name, filename)
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(body.get("content", ""))
    return {"ok": True}


@router.post("/templates")
async def create_template(body: dict):
    """创建新模板（复制 default 模板）"""
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="模板名称不能为空")
    src = os.path.join(TEMPLATES_DIR, "default")
    dst = os.path.join(TEMPLATES_DIR, name)
    if os.path.exists(dst):
        raise HTTPException(status_code=400, detail=f"模板 '{name}' 已存在")
    shutil.copytree(src, dst)
    return {"ok": True, "name": name}


@router.post("/configs/{workflow_name}/scan-models")
async def scan_workflow_models(
    workflow_name: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """扫描工作流 LLM 的可用模型"""
    config = await get_or_create_config(db, current_user.id, workflow_name)
    cfg = json.loads(config.config or "{}")
    base_url = body.get("base_url") or cfg.get("base_url", "https://api.openai.com/v1")
    api_key = body.get("api_key") or cfg.get("api_key", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="请先配置 API Key")
    url = base_url.rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {api_key}"}
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
    cfg["available_models"] = models
    config.config = json.dumps(cfg)
    await db.commit()
    return {"models": models, "selected": cfg.get("model", models[0] if models else "")}
