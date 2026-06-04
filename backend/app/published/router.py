"""已生成视频 API — 导出/列表/播放量"""
import os, json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sa_func, delete
from app.core.database import get_db
from app.core.deps import get_current_user
from app.auth.models import User
from app.published.models import PublishedVideo

router = APIRouter(prefix="/api/v1/published", tags=["published"])


@router.post("/export")
async def publish_video(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """导出视频：调 video-analyze 分析 → 存 published_videos"""
    from app.workers.workflow import call_workflow

    video_url = body.get("video_url", "")
    title = body.get("title", "未命名视频")
    source_session_id = body.get("session_id", 0)

    if not video_url:
        raise HTTPException(400, "video_url required")

    # 1. 调 material-embed 提取 scenes + tags
    scenes = []
    tags = []
    embed_data = {}
    try:
        embed_payload = {"material_type": "product", "video_url": video_url}
        embed_result = await call_workflow("material-embed", embed_payload)
        embed_data = embed_result.get("data") if isinstance(embed_result, dict) and "data" in embed_result else embed_result
        scenes = embed_data.get("scenes", []) if isinstance(embed_data, dict) else []
        if isinstance(embed_data, dict):
            tags = embed_data.get("video_tags", []) or embed_data.get("tags", [])
        print(f"[publish] material-embed got {len(scenes)} scenes, {len(tags)} tags")
    except Exception as e:
        print(f"[publish] material-embed failed: {e}")

    # 2. 调 video-analyze 分析
    analyze_result = {}
    if not scenes:
        scenes = [{"scene_id": 1, "time_range": "<00:00-00:05>", "description": title, "script": ""}]
    try:
        analyze_result = await call_workflow("video-analyze", {
            "scenes": scenes,
            "source_platform": "custom",
            "title": title,
            "category": "",
        })
    except Exception as e:
        print(f"[publish] video-analyze failed: {e}")

    # 合并 tags
    if isinstance(analyze_result, dict):
        analyze_tags = analyze_result.get("tags", [])
        if analyze_tags:
            tags = list(dict.fromkeys(tags + analyze_tags))

    # 计算节奏
    rhythm = 0.0
    if scenes:
        import re
        durs = []
        for sc in scenes:
            tr = sc.get("time_range", "")
            nums = re.findall(r"[\d.]+", tr)
            if len(nums) >= 2:
                d = float(nums[-1]) - float(nums[0])
                if d > 0:
                    durs.append(d)
        if durs:
            rhythm = round(sum(durs) / len(durs), 2)

    audio_features = body.get("audio_features", {})
    if not audio_features and video_url:
        # 尝试从本地视频提取音频特征
        import re, subprocess, tempfile, numpy as np, shutil
        m = re.search(r'/signed/[^/]+/(.+)', video_url)
        if m:
            local = '/app/uploads/' + m.group(1)
            if os.path.exists(local):
                tmpdir = tempfile.mkdtemp()
                try:
                    ap = os.path.join(tmpdir, "audio.wav")
                    subprocess.run(["ffmpeg", "-i", local, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-y", ap],
                        capture_output=True, text=True, timeout=120)
                    if os.path.exists(ap):
                        import librosa
                        y, sr = librosa.load(ap, sr=None, mono=True)
                        duration = float(librosa.get_duration(y=y, sr=sr))
                        tempo_val, _ = librosa.beat.beat_track(y=y, sr=sr)
                        bpm = float(np.atleast_1d(tempo_val)[0]) if tempo_val else 120.0
                        centroid_mean = float(np.atleast_1d(librosa.feature.spectral_centroid(y=y, sr=sr).mean())[0])
                        zcr_mean = float(np.atleast_1d(librosa.feature.zero_crossing_rate(y).mean())[0])
                        rolloff_mean = float(np.atleast_1d(librosa.feature.spectral_rolloff(y=y, sr=sr).mean())[0])
                        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
                        mfcc_mean = [round(float(np.atleast_1d(mfcc[i].mean())[0]), 4) for i in range(13)]
                        bpm_score = min(bpm / 2.0, 50.0)
                        cent_score = min(centroid_mean / 50.0, 25.0)
                        zcr_score = min(zcr_mean * 500, 25.0)
                        lightness = round(min(bpm_score + cent_score + zcr_score, 100), 1)
                        mood = "轻快" if lightness >= 55 else "中性" if lightness >= 30 else "稳重"
                        audio_features = {
                            "duration": round(duration, 2), "bpm": round(bpm, 1),
                            "spectral_centroid": round(centroid_mean, 2), "zero_crossing_rate": round(zcr_mean, 6),
                            "spectral_rolloff": round(rolloff_mean, 2), "mfcc_mean": mfcc_mean,
                            "lightness_score": lightness, "mood": mood,
                            "features": {"bpm_score": round(bpm_score, 1), "centroid_score": round(cent_score, 1), "zcr_score": round(zcr_score, 1)},
                        }
                        print(f"[publish] audio analysis: {mood}({lightness}) BPM={bpm}")
                except Exception as e:
                    print(f"[publish] audio analysis failed: {e}")
                finally:
                    shutil.rmtree(tmpdir, ignore_errors=True)

    pv = PublishedVideo(
        user_id=user.id,
        title=title,
        video_url=video_url,
        cover_url=body.get("cover_url", ""),
        analysis_report=analyze_result if isinstance(analyze_result, dict) else {},
        hook_method=analyze_result.get("hook_method", ""),
        selling_points=analyze_result.get("selling_points", []),
        style=analyze_result.get("style", ""),
        tags=tags,
        scenes=scenes,
        rhythm=rhythm,
        audio_features=audio_features,
        play_count=2000,
        source_session_id=source_session_id,
    )
    db.add(pv)
    await db.commit()
    await db.refresh(pv)

    return {"success": True, "id": pv.id, "video_url": video_url}


@router.get("/videos")
async def list_published(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    sort: str = Query("created_at", regex="^(created_at|play_count)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取已生成视频列表"""
    from app.published.models import PublishedVideo

    order_col = getattr(PublishedVideo, sort)
    order_fn = order_col.desc() if order == "desc" else order_col.asc()

    count_q = select(sa_func.count()).where(PublishedVideo.user_id == user.id)
    total = (await db.execute(count_q)).scalar() or 0

    q = select(PublishedVideo).where(
        PublishedVideo.user_id == user.id
    ).order_by(order_fn).offset(skip).limit(limit)
    rows = (await db.execute(q)).scalars().all()

    # 预测播放量：基于参考视频回归模型
    predicted_play_counts = {}
    try:
        from app.script.models import ReferenceVideo
        ref_q = select(ReferenceVideo).where(ReferenceVideo.user_id == str(user.id))
        refs = (await db.execute(ref_q)).scalars().all()
        if len(refs) >= 3:
            # 提取参考视频特征
            import math
            ref_features = []
            for ref in refs:
                af = ref.audio_features or {}
                ar = ref.analysis_report or {}
                ref_features.append({
                    "rhythm": ref.rhythm or 0.0,
                    "hook_quality": ar.get("hook_quality", 0) if isinstance(ar, dict) else 0,
                    "pacing_score": ar.get("pacing_score", 0) if isinstance(ar, dict) else 0,
                    "engagement_strength": ar.get("engagement_strength", 0) if isinstance(ar, dict) else 0,
                    "cta_clarity": ar.get("cta_clarity", 0) if isinstance(ar, dict) else 0,
                    "overall_score": ar.get("overall_score", 0) if isinstance(ar, dict) else 0,
                    "bpm": af.get("bpm", 0) or 0,
                    "lightness_score": af.get("lightness_score", 0) or 0,
                    "spectral_centroid": af.get("spectral_centroid", 0) or 0,
                    "zero_crossing_rate": af.get("zero_crossing_rate", 0) or 0,
                    "play_count": ref.play_count or 2000,
                })
            numeric_cols = ["rhythm", "hook_quality", "pacing_score", "engagement_strength",
                            "cta_clarity", "overall_score", "bpm", "lightness_score",
                            "spectral_centroid", "zero_crossing_rate"]
            for r in rows:
                ar = r.analysis_report or {}
                af = r.audio_features or {}
                features = {
                    "rhythm": r.rhythm or 0.0,
                    "hook_quality": ar.get("hook_quality", 0) if isinstance(ar, dict) else 0,
                    "pacing_score": ar.get("pacing_score", 0) if isinstance(ar, dict) else 0,
                    "engagement_strength": ar.get("engagement_strength", 0) if isinstance(ar, dict) else 0,
                    "cta_clarity": ar.get("cta_clarity", 0) if isinstance(ar, dict) else 0,
                    "overall_score": ar.get("overall_score", 0) if isinstance(ar, dict) else 0,
                    "bpm": af.get("bpm", 0) or 0,
                    "lightness_score": af.get("lightness_score", 0) or 0,
                    "spectral_centroid": af.get("spectral_centroid", 0) or 0,
                    "zero_crossing_rate": af.get("zero_crossing_rate", 0) or 0,
                }
                from statistics import median
                preds = []
                for col in numeric_cols:
                    vals = [(f[col], f["play_count"]) for f in ref_features]
                    xs = [v[0] for v in vals]
                    ys = [v[1] for v in vals]
                    n = len(xs)
                    mx, my = sum(xs)/n, sum(ys)/n
                    num = sum((xs[i]-mx)*(ys[i]-my) for i in range(n))
                    den = sum((xs[i]-mx)**2 for i in range(n))
                    slope = num / den if den > 0 else 0
                    intercept = my - slope * mx
                    input_val = features.get(col)
                    if input_val is not None and isinstance(input_val, (int, float)):
                        preds.append(slope * input_val + intercept)
                predicted_play_counts[r.id] = max(round(median(preds)) if preds else 2000, 2000)
    except Exception as e:
        print(f"[publish] predict failed: {e}")

    items = []
    for r in rows:
        items.append({
            "id": r.id,
            "title": r.title,
            "video_url": r.video_url,
            "cover_url": r.cover_url,
            "play_count": r.play_count,
            "predicted_play_count": predicted_play_counts.get(r.id, r.play_count),
            "hook_method": r.hook_method,
            "style": r.style,
            "tags": r.tags or [],
            "rhythm": r.rhythm or 0.0,
            "scenes": r.scenes or [],
            "analysis_report": r.analysis_report or {},
            "audio_features": r.audio_features or {},
            "created_at": r.created_at.isoformat() if r.created_at else "",
        })

    return {"total": total, "items": items}


@router.post("/{video_id}/view")
async def increment_view(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """增加播放量"""
    from app.published.models import PublishedVideo

    r = await db.get(PublishedVideo, video_id)
    if not r or r.user_id != user.id:
        raise HTTPException(404, "视频不存在")

    r.play_count = (r.play_count or 0) + 1
    await db.commit()
    return {"play_count": r.play_count}


@router.put("/{video_id}/play-count")
async def update_published_play_count(
    video_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """设置已生成视频播放量"""
    r = await db.get(PublishedVideo, video_id)
    if not r or r.user_id != user.id:
        raise HTTPException(404, "视频不存在")
    r.play_count = body.get("play_count", 2000)
    await db.commit()
    return {"play_count": r.play_count}


@router.delete("/{video_id}")
async def delete_published(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除已生成视频"""
    from app.published.models import PublishedVideo

    r = await db.get(PublishedVideo, video_id)
    if not r or r.user_id != user.id:
        raise HTTPException(404, "视频不存在")

    await db.delete(r)
    await db.commit()
    return {"success": True}
