"""工作流工作室 API — 基于 Session 文件夹存储"""
import json, os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.auth.models import User
from app.agent.models import ensure_session_dir

router = APIRouter(prefix="/api/v1/studio", tags=["studio"])

DEFAULT_STATE = {
    "products": [],
    "selected_product_id": None,
    "threshold": 30,
    "selected_material_ids": [],
    "collections": [],
    "selected_collection_id": None,
    "selected_template": "",
    "cached_materials": [],
}


def get_state_path(session_id: int) -> str:
    return os.path.join(ensure_session_dir(session_id)["root"], "workflow_state.json")


@router.get("/state/{session_id}")
async def get_workflow_state(session_id: int, user: User = Depends(get_current_user)):
    sp = get_state_path(session_id)
    if os.path.exists(sp):
        with open(sp, "r", encoding="utf-8") as f:
            return json.loads(f.read())
    return dict(DEFAULT_STATE)


@router.put("/state/{session_id}")
async def save_workflow_state(session_id: int, body: dict, user: User = Depends(get_current_user)):
    sp = get_state_path(session_id)
    with open(sp, "w", encoding="utf-8") as f:
        f.write(json.dumps(body, ensure_ascii=False, indent=2))
    return {"ok": True}


@router.post("/semantic-search")
async def semantic_search(body: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """产品介绍 → query-generate → material-search → 返回素材相似度列表"""
    from app.workers.workflow import call_workflow
    from app.material.search import search_materials_by_embeddings
    
    product_info = body.get("product_info", {})
    threshold = body.get("threshold", 30) / 100.0

    # 1. 调用 query-generate 生成关键词
    qg = await call_workflow("query-generate", {
        "product_info": {"product_id": 1, "name": product_info.get("title", ""), "description": product_info.get("content", "")},
        "video_style": "电商带货",
        "target_duration": 30,
    })
    product_queries = qg.get("product_queries", []) if isinstance(qg, dict) else []
    general_queries = qg.get("general_queries", []) if isinstance(qg, dict) else []

    # 2. 调用 material-search 生成向量
    ms = await call_workflow("material-search", {
        "product_queries": product_queries,
        "general_queries": general_queries,
    })
    embeddings = ms.get("product_embeddings", []) if isinstance(ms, dict) else []

    # 3. 用向量搜索 PG
    all_results = []
    seen = set()
    for emb in embeddings:
        vector = emb.get("embedding", [])
        if not vector:
            continue
        items = await search_materials_by_embeddings(db, str(user.id), vector, threshold)
        for item in items:
            item.pop("text_content", None)
            mid = item.get("id")
            if mid not in seen:
                seen.add(mid)
                all_results.append(item)

    all_results.sort(key=lambda r: r.get("similarity", 0), reverse=True)
    return {"materials": all_results, "total": len(all_results)}


@router.post("/generate-script")
async def studio_generate_script(body: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """直接生成剧本（不走LLM对话，直接调 runner 或 workflow）"""
    from app.workflow.runners.script_generate import run_script_generate
    from app.workflow.models import WorkflowConfig
    from sqlalchemy import select as _s
    import json, os

    product_content = body.get("product_content", "")
    template = body.get("template", "default")
    materials = body.get("materials", [])  # [{id, description, tags}]

    params = {
        "product_info": {"product_id": 1, "name": product_content[:30], "description": product_content, "selling_points": []},
        "style": "电商带货",
        "duration": 30,
        "selected_materials": materials,
    }

    # 查工作流配置
    wf = await db.execute(_s(WorkflowConfig).where(WorkflowConfig.user_id == user.id, WorkflowConfig.workflow_name == "script-generate"))
    wf_cfg = wf.scalar_one_or_none()
    script_dir = "/tmp"  # 临时返回，不存文件

    if wf_cfg and wf_cfg.enabled:
        cfg = json.loads(wf_cfg.config or "{}")
        if cfg.get("api_key") and cfg.get("base_url") and cfg.get("model"):
            result = await run_script_generate(api_key=cfg["api_key"], base_url=cfg["base_url"], model=cfg["model"], params=params, template=template)
            return result
    # fallback: 调 Coze workflow
    from app.workers.workflow import call_workflow
    result = await call_workflow("script-generate", params)
    return result


@router.post("/materials/search")
async def search_studio_materials(body: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """搜索素材（带阈值和标签）"""
    from sqlalchemy import select as _s, text as _t
    from app.material.models import Material
    threshold = body.get("threshold", 30) / 100.0
    tags = body.get("tags", [])
    query = _s(Material).where(Material.user_id == str(user.id))
    if tags:
        for tag in tags:
            query = query.where(Material.tags.contains(_t(f'"{tag}"')))
    r = await db.execute(query.order_by(Material.id.desc()))
    items = [{"id": m.id, "image_url": m.image_url, "tags": m.tags, "similarity": 1.0} for m in r.scalars().all()]
    return {"materials": items, "total": len(items)}
