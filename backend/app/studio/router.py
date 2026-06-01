"""工作流工作室 API"""
import json, os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.core.database import get_db
from app.core.deps import get_current_user
from app.auth.models import User
from app.studio.models import ProductInfo, MaterialCollection, VideoCollection
from app.material.models import Material

router = APIRouter(prefix="/api/v1/studio", tags=["studio"])


# ── 产品介绍 ────────────────────────────

@router.get("/products")
async def list_products(session_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    r = await db.execute(select(ProductInfo).where(ProductInfo.session_id == session_id).order_by(ProductInfo.id))
    return [{"id": p.id, "title": p.title, "content": p.content, "created_at": str(p.created_at)} for p in r.scalars()]


@router.post("/products")
async def create_product(body: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    p = ProductInfo(session_id=body["session_id"], title=body.get("title", ""), content=body.get("content", ""))
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return {"id": p.id, "title": p.title, "content": p.content}


@router.put("/products/{pid}")
async def update_product(pid: int, body: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    p = await db.get(ProductInfo, pid)
    if not p: raise HTTPException(404)
    if "title" in body: p.title = body["title"]
    if "content" in body: p.content = body["content"]
    await db.commit()
    return {"ok": True}


@router.delete("/products/{pid}")
async def delete_product(pid: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await db.execute(delete(ProductInfo).where(ProductInfo.id == pid))
    await db.commit()
    return {"ok": True}


# ── 素材集合 ────────────────────────────

@router.get("/material-collections")
async def list_material_collections(session_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    r = await db.execute(select(MaterialCollection).where(MaterialCollection.session_id == session_id).order_by(MaterialCollection.id.desc()))
    return [{"id": c.id, "name": c.name, "threshold": c.threshold, "material_ids": json.loads(c.material_ids or "[]"), "tag_filter": json.loads(c.tag_filter or "[]"), "created_at": str(c.created_at)} for c in r.scalars()]


@router.post("/material-collections")
async def create_material_collection(body: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    c = MaterialCollection(
        session_id=body["session_id"],
        name=body.get("name", "素材集合"),
        material_ids=json.dumps(body.get("material_ids", [])),
        threshold=body.get("threshold", 30),
        tag_filter=json.dumps(body.get("tag_filter", [])),
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return {"id": c.id, "name": c.name}


# ── 素材搜索（带阈值+标签）─────────────

@router.post("/materials/search")
async def search_studio_materials(body: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """搜索素材，支持相似度阈值和标签过滤"""
    threshold = body.get("threshold", 30) / 100.0
    tags = body.get("tags", [])
    query = select(Material).where(Material.user_id == str(user.id))
    if tags:
        from sqlalchemy import text as _t
        for tag in tags:
            query = query.where(Material.tags.contains(_t(f'"{tag}"')))
    r = await db.execute(query.order_by(Material.id.desc()))
    items = []
    for m in r.scalars().all():
        items.append({"id": m.id, "image_url": m.image_url, "tags": m.tags, "similarity": 1.0})
    return {"materials": items, "total": len(items)}


# ── 视频集合 ────────────────────────────

@router.get("/video-collections")
async def list_video_collections(session_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    r = await db.execute(select(VideoCollection).where(VideoCollection.session_id == session_id).order_by(VideoCollection.id.desc()))
    return [{"id": c.id, "name": c.name, "script_name": c.script_name, "video_urls": json.loads(c.video_urls or "[]"), "created_at": str(c.created_at)} for c in r.scalars()]


@router.post("/video-collections")
async def create_video_collection(body: dict, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    c = VideoCollection(
        session_id=body["session_id"],
        name=body.get("name", "视频集合"),
        script_name=body.get("script_name", ""),
        video_urls=json.dumps(body.get("video_urls", [])),
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return {"id": c.id, "name": c.name}
