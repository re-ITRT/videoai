import os
import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
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
from app.material import search as search_svc

router = APIRouter(prefix="/api/v1/materials", tags=["materials"])


# ── Upload ────────────────────────────────

@router.post("/upload", response_model=MaterialUploadResponse)
async def upload_material(
    request: MaterialUploadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传素材并保存，素材切片由 material-embed 工作流的 scenes 解析"""
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

    # 解析 material-embed 工作流的 scenes → 创建切片
    if request.scenes:
        await svc.parse_and_create_slices(db, material.id, request.scenes)

    return MaterialUploadResponse.model_validate(material)


# ── File Upload ────────────────────────────

UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload/file")
async def upload_material_file(
    file: UploadFile = File(...),
    material_type: str = Form("product"),
    input_type: str = Form("image"),
    category: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传素材文件（图片/视频），保存文件并创建素材记录"""
    ext = os.path.splitext(file.filename or "file")[1] or ".bin"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOAD_DIR / filename

    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    image_url = f"/uploads/{filename}"

    material = await svc.create_material(
        db=db,
        user_id=str(current_user.id),
        material_type=material_type,
        input_type=input_type,
        image_url=image_url,
        source="upload",
    )

    return {
        "id": material.id,
        "material_type": material.material_type,
        "input_type": material.input_type,
        "image_url": image_url,
        "source": "upload",
        "created_at": material.created_at,
    }


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
async def search_materials(  # pragma: no cover
    request: MaterialSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """语义检索 — 调 material-search 工作流 → pgvector 阈值筛选"""
    try:
        results = await search_svc.search_materials(
            db=db,
            user_id=str(current_user.id),
            query=request.query,
            threshold=request.threshold,
            max_results=request.max_results,
            search_level=request.search_level,
        )
    except Exception as e:
        # pgvector 不可用时回退到文本搜索
        try:
            results = await search_svc.search_materials_fallback(
                db=db,
                user_id=str(current_user.id),
                query=request.query,
                max_results=request.max_results,
            )
        except Exception:
            results = []

    return [
        MaterialSearchResult(
            id=r["id"],
            similarity=float(r.get("similarity", 0)),
            image_url=r.get("image_url"),
            text_content=r.get("text_content"),
            tags=r.get("tags", []),
        )
        for r in results
    ]


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
