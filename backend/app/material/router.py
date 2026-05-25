from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.auth.models import User
from app.material.schemas import (
    MaterialUploadRequest, MaterialUploadResponse, MaterialResponse,
    SliceCreateRequest, SliceResponse,
    MaterialSearchRequest, MaterialSearchResult,
)
from app.material import service as svc

router = APIRouter(prefix="/api/v1/materials", tags=["materials"])


# ── Upload ────────────────────────────────

@router.post("/upload", response_model=MaterialUploadResponse)
async def upload_material(
    request: MaterialUploadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传素材并保存，视频素材自动创建默认切片"""
    material = await svc.create_material(
        db=db,
        user_id=str(current_user.id),
        material_type=request.material_type,
        input_type=request.input_type,
        product_id=request.product_id,
        image_url=request.image_url,
        text_content=request.text_content,
        source=request.source,
    )

    # 视频素材自动创建默认切片
    if request.input_type == "video":
        await svc.create_video_slices(db, material.id, scene_count=3)

    return MaterialUploadResponse.model_validate(material)


# ── List ──────────────────────────────────

@router.get("", response_model=list[MaterialResponse])
async def list_materials(
    material_type: str | None = Query(None, description="筛选类型: product/general/reference"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """素材列表"""
    materials = await svc.list_materials(
        db=db,
        user_id=str(current_user.id),
        material_type=material_type,
        skip=skip,
        limit=limit,
    )
    return [MaterialResponse.model_validate(m) for m in materials]


# ── Get single ────────────────────────────

@router.get("/{material_id}", response_model=MaterialResponse)
async def get_material(
    material_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """素材详情"""
    material = await svc.get_material(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="素材不存在")
    return MaterialResponse.model_validate(material)


# ── Delete ────────────────────────────────

@router.delete("/{material_id}", status_code=204)
async def delete_material(
    material_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除素材（级联删除切片）"""
    ok = await svc.delete_material(db, material_id)
    if not ok:
        raise HTTPException(status_code=404, detail="素材不存在")


# ── Search ────────────────────────────────

@router.post("/search", response_model=list[MaterialSearchResult])
async def search_materials(
    request: MaterialSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """语义检索（骨架 — 待集成 pgvector 相似度查询）"""
    # TODO: 集成 pgvector <=> 余弦相似度查询
    # 当前返回空结果，占位
    return []


# ═══════════════════════════════════════════
# Slice 子路由
# ═══════════════════════════════════════════

@router.get("/{material_id}/slices", response_model=list[SliceResponse])
async def list_slices(
    material_id: int,
    slice_type: str | None = Query(None, description="筛选类型: video_scene/keyframe/audio_segment"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取素材的切片列表（M4）"""
    material = await svc.get_material(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="素材不存在")
    slices = await svc.list_slices(db, material_id, slice_type=slice_type)
    return [SliceResponse.model_validate(s) for s in slices]


@router.post("/{material_id}/slices", response_model=SliceResponse, status_code=201)
async def create_slice(
    material_id: int,
    request: SliceCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动为素材添加切片"""
    material = await svc.get_material(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="素材不存在")
    slice_ = await svc.create_slice(
        db=db,
        material_id=material_id,
        slice_type=request.slice_type,
        scene_id=request.scene_id,
        time_range=request.time_range,
        description=request.description,
        image_url=request.image_url,
    )
    return SliceResponse.model_validate(slice_)
