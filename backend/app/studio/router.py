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
    "selected_template": "",
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
