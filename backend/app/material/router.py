import asyncio
import os
import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.database import async_session
from app.core.deps import get_current_user
from app.auth.models import User
from app.material.schemas import (
    MaterialUploadRequest, MaterialUploadResponse, MaterialResponse,
    SliceCreateRequest, SliceResponse,
    MaterialSearchRequest, MaterialSearchResult,
)
from app.material import service as svc
from app.material import search as search_svc
from app.core.signer import generate_signed_url
from app.workers.workflow import call_workflow

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
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)  # pragma: no cover


@router.post("/upload/file")
async def upload_material_file(
    file: UploadFile = File(None),
    material_type: str = Form("product"),
    input_type: str = Form("image"),
    category: str = Form(None),
    name: str = Form(""),
    text_content: str = Form(None),
    product_name: str = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传素材文件（图片/视频），保存文件并创建素材记录"""
    image_url = None
    signed_url = None
    if file and file.filename:
        ext = os.path.splitext(file.filename or "file")[1] or ".bin"
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = UPLOAD_DIR / filename
        with open(filepath, "wb") as f:
            shutil.copyfileobj(file.file, f)
        image_url = f"/uploads/{filename}"
        signed_url = generate_signed_url(image_url, expire_seconds=31536000)

    material = await svc.create_material(
        db=db,
        user_id=str(current_user.id),
        material_type=material_type,
        input_type=input_type,
        image_url=image_url,
        text_content=text_content,
        name=name,
        source="upload",
    )
    # 异步触发 material-embed 工作流（不阻塞返回）
    if not signed_url:
        return {
            "id": material.id,
            "material_type": material.material_type,
            "input_type": material.input_type,
            "image_url": image_url,
            "source": "upload",
            "created_at": material.created_at,
        }
    
    import logging
    embed_logger = logging.getLogger("material-embed")

    # 音频素材：直接标记完成 + 跑 Librosa 分析
    if material_type == "audio" or input_type == "audio":  # pragma: no cover
        try:
            tags = ["BGM", category or "音频"] if category else ["BGM"]
            # Librosa 分析
            audio_features = {}
            try:
                import librosa
                import numpy as np
                filepath = UPLOAD_DIR / filename
                y, sr = librosa.load(str(filepath), sr=None, mono=True)
                duration = float(librosa.get_duration(y=y, sr=sr))
                tempo_val, _ = librosa.beat.beat_track(y=y, sr=sr)
                bpm = float(np.atleast_1d(tempo_val)[0]) if tempo_val else 120.0
                cent = librosa.feature.spectral_centroid(y=y, sr=sr)
                centroid_mean = float(np.atleast_1d(cent.mean())[0])
                zcr = librosa.feature.zero_crossing_rate(y)
                zcr_mean = float(np.atleast_1d(zcr.mean())[0])
                rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
                rolloff_mean = float(np.atleast_1d(rolloff.mean())[0])
                mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
                mfcc_mean = [round(float(np.atleast_1d(mfcc[i].mean())[0]), 4) for i in range(13)]
                bpm_score = min(bpm / 2.0, 50.0)
                cent_score = min(centroid_mean / 50.0, 25.0)
                zcr_score = min(zcr_mean * 500, 25.0)
                lightness = round(min(bpm_score + cent_score + zcr_score, 100), 1)
                mood = "稳重" if lightness < 30 else "中性" if lightness < 55 else "轻快"
                audio_features = {
                    "duration": round(duration, 2), "bpm": round(bpm, 1),
                    "spectral_centroid": round(centroid_mean, 2),
                    "zero_crossing_rate": round(zcr_mean, 6),
                    "spectral_rolloff": round(rolloff_mean, 2),
                    "mfcc_mean": mfcc_mean,
                    "lightness_score": lightness, "mood": mood,
                    "features": {"bpm_score": round(bpm_score, 1), "centroid_score": round(cent_score, 1), "zcr_score": round(zcr_score, 1)},
                }
            except Exception as ae:
                embed_logger.error(f"audio material {material.id} librosa analysis failed: {ae}")
            async with async_session() as session:
                m = await session.get(type(material), material.id)
                if m:
                    m.tags = tags
                    if audio_features:
                        m.audio_features = audio_features
                    await session.commit()
            embed_logger.info(f"audio material {material.id}: tagged+analyzed done")
        except Exception as e:
            embed_logger.error(f"audio material {material.id} tag failed: {e}")
        return {
            "id": material.id,
            "material_type": material.material_type,
            "input_type": material.input_type,
            "image_url": image_url,
            "source": "upload",
            "created_at": material.created_at,
        }

    async def run_embed():  # pragma: no cover
        try:
            public_url = f"http://114.117.242.17:3000{signed_url}"
            embed_logger.info(f"Starting material-embed for material {material.id}, url={public_url[:60]}...")
            brief = text_content or category or f"上传的{material_type}素材"
            result = await call_workflow("material-embed", {
                "image_url": public_url,
                "brief_description": brief,
                "material_type": "product",
            })
            # Coze webhook 响应可能是 {code, data} 格式
            data = result.get("data") if isinstance(result, dict) and "data" in result else result
            if isinstance(data, dict):
                scenes = data.get("scenes", [])
                tags = data.get("video_tags", []) or data.get("tags", [])
                image_emb = data.get("image_embedding", [])
            else:
                scenes = result.get("scenes", [])
                tags = result.get("video_tags", [])
                image_emb = result.get("image_embedding", [])
            # 保存嵌入结果到 material 记录
            async with async_session() as session:
                m = await session.get(type(material), material.id)
                if m:
                    if tags:
                        m.tags = tags
                    if image_emb:
                        from sqlalchemy import text as sa_text
                        vec_str = "[" + ",".join(str(v) for v in image_emb) + "]"
                        await session.execute(
                            sa_text("UPDATE materials SET embedding = CAST(:vec AS vector) WHERE id = :id"),
                            {"vec": vec_str, "id": m.id},
                        )
                    if scenes:
                        from app.material import service as mat_svc
                        await mat_svc.parse_and_create_slices(session, m.id, scenes)
                    await session.commit()
        except Exception as e:
            embed_logger.error(f"material-embed failed for material {material.id}: {e}")

    asyncio.create_task(run_embed())

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
