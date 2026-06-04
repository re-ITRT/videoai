"""多因子归因分析 API"""
import os, json, math, re
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_user
from app.auth.models import User

router = APIRouter(prefix="/api/v1/attribution", tags=["attribution"])


def _extract_features(ref_video) -> dict:
    """从 ReferenceVideo 提取平展特征"""
    af = ref_video.audio_features or {}
    ar = ref_video.analysis_report or {}
    return {
        "id": ref_video.id,
        "title": ref_video.title or "",
        "category": ref_video.category or "",
        "style": ref_video.style or "",
        "hook_method": ref_video.hook_method or "",
        "tags": ref_video.tags or [],
        "selling_points": ref_video.selling_points or [],
        "rhythm": ref_video.rhythm or 0.0,
        "play_count": ref_video.play_count or 2000,
        # analysis_report 数值评分
        "hook_quality": ar.get("hook_quality", 0) if isinstance(ar, dict) else 0,
        "pacing_score": ar.get("pacing_score", 0) if isinstance(ar, dict) else 0,
        "engagement_strength": ar.get("engagement_strength", 0) if isinstance(ar, dict) else 0,
        "cta_clarity": ar.get("cta_clarity", 0) if isinstance(ar, dict) else 0,
        "overall_score": ar.get("overall_score", 0) if isinstance(ar, dict) else 0,
        # BGM 特征
        "bpm": af.get("bpm", 0) or 0,
        "lightness_score": af.get("lightness_score", 0) or 0,
        "spectral_centroid": af.get("spectral_centroid", 0) or 0,
        "zero_crossing_rate": af.get("zero_crossing_rate", 0) or 0,
    }


@router.get("/data")
async def get_attribution_data(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """返回所有参考视频的平展特征数据"""
    from app.script.models import ReferenceVideo
    q = select(ReferenceVideo).where(ReferenceVideo.user_id == str(user.id)).order_by(ReferenceVideo.id)
    rows = (await db.execute(q)).scalars().all()
    return {"items": [_extract_features(r) for r in rows]}


@router.post("/analyze")
async def run_attribution_analysis(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """多因子归因分析：相关性 + 回归 + 特征重要性 + 最佳组合"""
    from app.script.models import ReferenceVideo
    q = select(ReferenceVideo).where(ReferenceVideo.user_id == str(user.id))
    rows = (await db.execute(q)).scalars().all()
    if len(rows) < 3:
        raise HTTPException(400, "至少需要3个参考视频才能分析")

    # 提取特征
    features = [_extract_features(r) for r in rows]

    # 数值特征列
    numeric_cols = ["rhythm", "hook_quality", "pacing_score", "engagement_strength",
                    "cta_clarity", "overall_score", "bpm", "lightness_score",
                    "spectral_centroid", "zero_crossing_rate"]

    # 分类特征列
    cat_cols = ["category", "style", "hook_method"]

    # 1. 相关性矩阵（Pearson）
    all_numeric = numeric_cols + ["play_count"]
    corr_matrix = {}
    for c1 in all_numeric:
        corr_matrix[c1] = {}
        vals1 = [f[c1] for f in features if isinstance(f.get(c1), (int, float))]
        for c2 in all_numeric:
            vals2 = [f[c2] for f in features if isinstance(f.get(c2), (int, float))]
            n = min(len(vals1), len(vals2))
            if n < 3:
                corr_matrix[c1][c2] = 0
                continue
            v1 = vals1[:n]
            v2 = vals2[:n]
            m1, m2 = sum(v1)/n, sum(v2)/n
            num = sum((v1[i]-m1)*(v2[i]-m2) for i in range(n))
            d1 = math.sqrt(sum((v1[i]-m1)**2 for i in range(n)))
            d2 = math.sqrt(sum((v2[i]-m2)**2 for i in range(n)))
            corr_matrix[c1][c2] = round(num / (d1*d2) if d1*d2 > 0 else 0, 4)

    # 2. 单变量回归（每个特征对播放量）
    regression = []
    for col in numeric_cols:
        vals = [(f[col], f["play_count"]) for f in features if isinstance(f.get(col), (int, float))]
        if len(vals) < 3:
            continue
        xs = [v[0] for v in vals]
        ys = [v[1] for v in vals]
        n = len(xs)
        mx, my = sum(xs)/n, sum(ys)/n
        num = sum((xs[i]-mx)*(ys[i]-my) for i in range(n))
        den = sum((xs[i]-mx)**2 for i in range(n))
        slope = num / den if den > 0 else 0
        intercept = my - slope * mx
        # R²
        ss_res = sum((ys[i] - (slope*xs[i] + intercept))**2 for i in range(n))
        ss_tot = sum((ys[i] - my)**2 for i in range(n))
        r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
        regression.append({
            "feature": col,
            "slope": round(slope, 4),
            "intercept": round(intercept, 2),
            "r2": round(r2, 4),
            "correlation": corr_matrix.get(col, {}).get("play_count", 0),
        })
    regression.sort(key=lambda x: abs(x["correlation"]), reverse=True)

    # 3. 特征重要性（|correlation| 归一化）
    corrs_with_pc = [(col, abs(corr_matrix.get(col, {}).get("play_count", 0))) for col in numeric_cols]
    total = sum(c[1] for c in corrs_with_pc) or 1
    importance = [{"feature": c[0], "importance": round(c[1]/total*100, 1)} for c in corrs_with_pc]
    importance.sort(key=lambda x: x["importance"], reverse=True)

    # 4. 最佳组合（分类特征 × BGM 分段）
    best_combos = []
    for f in features:
        bgm_level = "轻快" if f["lightness_score"] >= 55 else ("中性" if f["lightness_score"] >= 30 else "稳重") if f["lightness_score"] else "无BGM"
        rhythm_tag = "快" if f["rhythm"] <= 2 else ("中" if f["rhythm"] <= 5 else "慢") if f["rhythm"] else "未知"
        combo_key = f"{f['style']}|{f['hook_method'][:12]}|{bgm_level}|{rhythm_tag}"
        best_combos.append({
            "combo": combo_key,
            "style": f["style"],
            "hook_method": f["hook_method"],
            "bgm": bgm_level,
            "rhythm_tag": rhythm_tag,
            "play_count": f["play_count"],
            "title": f["title"][:20],
        })
    # 按组合分组求平均
    from collections import defaultdict
    groups = defaultdict(list)
    for c in best_combos:
        groups[c["combo"]].append(c)
    combo_rank = []
    for k, v in groups.items():
        avg_pc = round(sum(c["play_count"] for c in v) / len(v))
        first = v[0]
        combo_rank.append({
            "combo": k, "avg_play_count": avg_pc, "count": len(v),
            "style": first.get("style", ""),
            "hook_method": first.get("hook_method", ""),
            "bgm": first.get("bgm", ""),
            "rhythm_tag": first.get("rhythm_tag", ""),
        })
    combo_rank.sort(key=lambda x: x["avg_play_count"], reverse=True)

    return {
        "correlation_matrix": corr_matrix,
        "regression": regression,
        "feature_importance": importance,
        "best_combos": combo_rank[:20],
        "sample_count": len(features),
        "numeric_features": numeric_cols,
    }


@router.post("/predict")
async def predict_play_count(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """根据已有参考视频的回归模型，预测输入视频的播放量"""
    from app.script.models import ReferenceVideo
    q = select(ReferenceVideo).where(ReferenceVideo.user_id == str(user.id))
    rows = (await db.execute(q)).scalars().all()
    if len(rows) < 3:
        return {"predicted_play_count": 2000, "confidence": "low", "message": "样本不足3个，返回默认值"}

    # 提取训练特征
    train = [_extract_features(r) for r in rows]
    numeric_cols = ["rhythm", "hook_quality", "pacing_score", "engagement_strength",
                    "cta_clarity", "overall_score", "bpm", "lightness_score",
                    "spectral_centroid", "zero_crossing_rate"]

    # 计算每个特征的回归系数
    predictions = []
    for col in numeric_cols:
        vals = [(f[col], f["play_count"]) for f in train if isinstance(f.get(col), (int, float))]
        if len(vals) < 3:
            continue
        xs = [v[0] for v in vals]
        ys = [v[1] for v in vals]
        n = len(xs)
        mx, my = sum(xs)/n, sum(ys)/n
        num = sum((xs[i]-mx)*(ys[i]-my) for i in range(n))
        den = sum((xs[i]-mx)**2 for i in range(n))
        slope = num / den if den > 0 else 0
        intercept = my - slope * mx
        # 用该特征预测
        input_val = body.get(col)
        if input_val is not None and isinstance(input_val, (int, float)):
            pred = slope * input_val + intercept
            predictions.append(pred)

    if not predictions:
        return {"predicted_play_count": 2000, "confidence": "none"}

    from statistics import median
    predicted = round(median(predictions))
    # 置信度：基于预测值的标准差评估
    return {
        "predicted_play_count": max(predicted, 0),
        "confidence": "medium" if len(predictions) >= 5 else "low",
        "features_used": len(predictions),
    }
