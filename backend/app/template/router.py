"""
灵感模板+策略因子 - API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from .schemas import (
    StrategyFactorCreate,
    StrategyFactorUpdate,
    StrategyFactorResponse,
    FactorListResponse,
    InspirationTemplateCreate,
    InspirationTemplateUpdate,
    InspirationTemplateResponse,
    TemplateListResponse,
    GenerateFromTemplateRequest,
)
from .service import (
    create_factor,
    get_factors,
    get_factor_by_id,
    update_factor,
    delete_factor,
    create_template,
    get_templates,
    get_template_by_id,
    update_template,
    delete_template,
    generate_script_from_template,
    DEFAULT_USER_ID,
)

router = APIRouter(prefix="/api/v1/template", tags=["template"])


# ── Strategy Factor Routes ─────────────────

@router.post("/factors", response_model=StrategyFactorResponse)
async def create_factor_endpoint(
    data: StrategyFactorCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建策略因子"""
    return await create_factor(db, DEFAULT_USER_ID, data)


@router.get("/factors", response_model=FactorListResponse)
async def list_factors(
    factor_type: Optional[str] = Query(None, description="按因子类型筛选：hook / scene / narration / visual / ending"),
    category: Optional[str] = Query(None, description="按分类筛选"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取策略因子列表"""
    total, factors = await get_factors(db, DEFAULT_USER_ID, factor_type, category, skip, limit)
    return FactorListResponse(total=total, items=factors)


@router.get("/factors/{factor_id}", response_model=StrategyFactorResponse)
async def get_factor(
    factor_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取策略因子详情"""
    factor = await get_factor_by_id(db, factor_id, DEFAULT_USER_ID)
    if not factor:
        raise HTTPException(status_code=404, detail="因子不存在")
    return factor


@router.put("/factors/{factor_id}", response_model=StrategyFactorResponse)
async def update_factor_endpoint(
    factor_id: int,
    data: StrategyFactorUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新策略因子"""
    factor = await update_factor(db, factor_id, DEFAULT_USER_ID, data)
    if not factor:
        raise HTTPException(status_code=404, detail="因子不存在")
    return factor


@router.delete("/factors/{factor_id}")
async def delete_factor_endpoint(
    factor_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除策略因子"""
    success = await delete_factor(db, factor_id, DEFAULT_USER_ID)
    if not success:
        raise HTTPException(status_code=404, detail="因子不存在")
    return {"success": True, "message": "删除成功"}


# ── Inspiration Template Routes ─────────────────

@router.post("/templates", response_model=InspirationTemplateResponse)
async def create_template_endpoint(
    data: InspirationTemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建灵感模板"""
    return await create_template(db, DEFAULT_USER_ID, data)


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    category: Optional[str] = Query(None, description="按分类筛选"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取灵感模板列表"""
    total, templates = await get_templates(db, DEFAULT_USER_ID, category, skip, limit)
    return TemplateListResponse(total=total, items=templates)


@router.get("/templates/{template_id}", response_model=InspirationTemplateResponse)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取灵感模板详情"""
    template = await get_template_by_id(db, template_id, DEFAULT_USER_ID)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return template


@router.put("/templates/{template_id}", response_model=InspirationTemplateResponse)
async def update_template_endpoint(
    template_id: int,
    data: InspirationTemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新灵感模板"""
    template = await update_template(db, template_id, DEFAULT_USER_ID, data)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return template


@router.delete("/templates/{template_id}")
async def delete_template_endpoint(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除灵感模板"""
    success = await delete_template(db, template_id, DEFAULT_USER_ID)
    if not success:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"success": True, "message": "删除成功"}


# ── Generate Script from Template ─────────────────

@router.post("/templates/{template_id}/generate-script")
async def generate_script(
    template_id: int,
    request: GenerateFromTemplateRequest,
    db: AsyncSession = Depends(get_db),
):
    """使用模板生成剧本"""
    try:
        result = await generate_script_from_template(db, DEFAULT_USER_ID, request)
        return {
            "success": True,
            "template_id": template_id,
            "script": result,
            "message": "剧本生成成功"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


# ── AI Template Generation ─────────────────

@router.get("/attribution-insights")
async def get_attribution_insights(
    db: AsyncSession = Depends(get_db),
):
    """获取归因分析洞察：最佳组合 + 特征重要性 + 推荐策略"""
    from app.script.models import ReferenceVideo
    from sqlalchemy import select as _sel
    q = _sel(ReferenceVideo).limit(100)
    rows = (await db.execute(q)).scalars().all()
    if len(rows) < 3:
        return {"insights": [], "message": f"至少需要3个参考视频，当前{len(rows)}个"}

    import math
    # 提取特征
    features = []
    for r in rows:
        af = r.audio_features or {}
        ar = r.analysis_report or {}
        features.append({
            "id": r.id, "title": r.title or "",
            "style": r.style or "", "hook_method": r.hook_method or "",
            "rhythm": r.rhythm or 0.0, "play_count": r.play_count or 2000,
            "hook_quality": ar.get("hook_quality", 0) if isinstance(ar, dict) else 0,
            "pacing_score": ar.get("pacing_score", 0) if isinstance(ar, dict) else 0,
            "engagement_strength": ar.get("engagement_strength", 0) if isinstance(ar, dict) else 0,
            "cta_clarity": ar.get("cta_clarity", 0) if isinstance(ar, dict) else 0,
            "overall_score": ar.get("overall_score", 0) if isinstance(ar, dict) else 0,
            "bpm": af.get("bpm", 0) or 0, "lightness_score": af.get("lightness_score", 0) or 0,
        })

    # 最佳组合
    from collections import defaultdict
    groups = defaultdict(list)
    for f in features:
        bgm = "轻快" if f["lightness_score"] >= 55 else ("中性" if f["lightness_score"] >= 30 else "稳重") if f["lightness_score"] else "无BGM"
        rt = "快" if f["rhythm"] <= 2 else ("中" if f["rhythm"] <= 5 else "慢")
        key = f"{f['style']}|{f['hook_method'][:10]}|{bgm}|{rt}"
        groups[key].append(f)
    combos = []
    for k, v in groups.items():
        parts = k.split("|")
        avg_pc = round(sum(c["play_count"] for c in v) / len(v))
        combos.append({"combo": k, "style": parts[0], "hook": parts[1], "bgm": parts[2], "rhythm": parts[3],
                       "avg_play_count": avg_pc, "count": len(v)})
    combos.sort(key=lambda x: x["avg_play_count"], reverse=True)

    # 最佳特征（依据重要性排序）
    numeric_cols = ["hook_quality", "pacing_score", "engagement_strength", "cta_clarity", "overall_score"]
    corrs = {}
    for col in numeric_cols:
        vals = [(f[col], f["play_count"]) for f in features if isinstance(f.get(col), (int, float))]
        if len(vals) < 3: continue
        xs, ys = zip(*vals)
        n = len(xs)
        mx, my = sum(xs)/n, sum(ys)/n
        num = sum((xs[i]-mx)*(ys[i]-my) for i in range(n))
        d1 = math.sqrt(sum((xs[i]-mx)**2 for i in range(n)))
        d2 = math.sqrt(sum((ys[i]-my)**2 for i in range(n)))
        corrs[col] = round(num/(d1*d2) if d1*d2 > 0 else 0, 4)
    top_features = sorted(corrs.items(), key=lambda x: abs(x[1]), reverse=True)

    # 模板分析
    template_analysis = {}
    from app.published.models import PublishedVideo as PV
    pub_rows = (await db.execute(_sel(PV).limit(100))).scalars().all()
    tpl_groups = {}
    for p in pub_rows:
        t = p.script_template or "default"
        if t not in tpl_groups:
            tpl_groups[t] = {"count": 0, "total_play": 0, "titles": []}
        tpl_groups[t]["count"] += 1
        tpl_groups[t]["total_play"] += (p.play_count or 2000)
        tpl_groups[t]["titles"].append(p.title or "未命名")
    template_analysis = {}
    for t, d in tpl_groups.items():
        avg = round(d["total_play"] / d["count"]) if d["count"] else 0
        template_analysis[t] = {"count": d["count"], "avg_play_count": avg,
                                "feedback": _get_template_feedback(t, avg, d["count"])}

    return {
        "best_combos": combos[:10],
        "top_features": [{"name": n, "correlation": v} for n, v in top_features],
        "sample_count": len(features),
        "template_analysis": template_analysis,
    }


def _get_template_feedback(template_name: str, avg_play_count: int, sample_count: int) -> str:
    if sample_count == 0:
        return "暂无数据"
    if avg_play_count >= 10000:
        return f"表现优秀（平均播放量{avg_play_count}），建议推广此模板"
    elif avg_play_count >= 5000:
        return f"表现良好（平均播放量{avg_play_count}），可继续优化"
    elif sample_count <= 2:
        return f"仅{sample_count}个样本，平均播放量{avg_play_count}，需更多数据评估"
    return f"平均播放量{avg_play_count}较低，建议调整模板策略"


@router.post("/templates/optimize")
async def optimize_template(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """根据归因分析+已生成视频数据，给出特定剧本模板的优化建议"""
    template_name = body.get("template_name", "default")
    from app.published.models import PublishedVideo
    from app.script.models import ReferenceVideo
    from sqlalchemy import select as _sel
    import json, httpx, math

    # 获取模板使用数据
    pub_videos = (await db.execute(
        _sel(PublishedVideo).where(PublishedVideo.script_template == template_name)
    )).scalars().all()

    # 获取参考视频最佳组合
    refs = (await db.execute(_sel(ReferenceVideo).limit(100))).scalars().all()

    # 构造数据
    pub_count = len(pub_videos)
    avg_play = round(sum(p.play_count or 2000 for p in pub_videos) / pub_count) if pub_count else 0

    # 最佳组合（从参考视频提取）
    combo_counts = {}
    for r in refs:
        af = r.audio_features or {}
        bgm = "轻快" if (af.get("lightness_score") or 0) >= 55 else "稳重"
        key = (r.style or "?", (r.hook_method or "")[:8], bgm)
        combo_counts[key] = combo_counts.get(key, 0) + 1
    best_combos = sorted(combo_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    combo_text = "; ".join([f"{s}/{h}/{b}({c}条)" for (s, h, b), c in best_combos])

    # 调用LLM
    wf_cfg = None
    try:
        from app.workflow.models import WorkflowConfig
        from sqlalchemy import select as _s
        wf_cfg = (await db.execute(
            _s(WorkflowConfig).where(
                WorkflowConfig.workflow_name == "material-analyze",
                WorkflowConfig.enabled == 1
            ).limit(1)
        )).scalar_one_or_none()
    except: pass

    if wf_cfg:
        cfg = json.loads(wf_cfg.config or "{}")
        api_key = cfg.get("api_key")
        base_url = (cfg.get("base_url") or "https://api.deepseek.com/v1").rstrip("/")
        model = cfg.get("model", "deepseek-v4-flash")

        prompt = f"""你是一个电商短视频策略优化专家。分析以下数据，给剧本模板「{template_name}」输出3条具体可执行的优化建议。

【模板使用情况】
使用次数：{pub_count}次
平均播放量：{avg_play}
模板风格/标签：{template_name}

【参考视频最佳组合（风格/Hook/BGM，引用次数）】
{combo_text}

【高播放量特征相关性】
参考已有归因数据中不同特征对播放量的影响

请输出JSON（不要其他文本）：
{{
  "summary": "对该模板当前表现的一句话总结",
  "suggestions": [
    {{
      "aspect": "优化方面（Hook/风格/BGM/节奏/结构等）",
      "suggestion": "具体优化建议",
      "expected_impact": "预期效果描述"
    }}
  ],
  "priority": "高/中/低（优化优先级）"
}}"""

        try:
            payload = {
                "model": model, "temperature": 0.7,
                "messages": [
                    {"role": "system", "content": "你是电商短视频策略优化专家，输出结构化JSON。"},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
            }
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(f"{base_url}/chat/completions", json=payload,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
                if resp.status_code == 200:
                    c = resp.json()["choices"][0]["message"]["content"]
                    return {"source": "ai", "template": template_name, **json.loads(c)}
        except Exception as e:
            print(f"[optimize] LLM failed: {e}")

    # fallback
    suggestions = []
    if pub_count == 0:
        suggestions.append({"aspect": "模板未使用", "suggestion": f"该模板尚未用于生成视频，建议先使用一次获取数据", "expected_impact": "获取基线数据"})
    if best_combos:
        s, h, b = best_combos[0][0]
        suggestions.append({"aspect": "风格/Hook", "suggestion": f"参考高引用组合：{s}风格+{h}Hook+{b}BGM，建议在模板中融入这些元素", "expected_impact": "提升播放量潜力"})
    suggestions.append({"aspect": "持续优化", "suggestion": "每导出3-5个视频后重新评估模板效果", "expected_impact": "数据驱动的迭代优化"})

    return {
        "source": "data", "template": template_name,
        "summary": f"模板「{template_name}」已使用{pub_count}次，平均播放量{avg_play}。建议根据归因数据优化。",
        "suggestions": suggestions,
        "priority": "中",
    }


@router.post("/templates/ai-generate")
async def ai_generate_template(
    db: AsyncSession = Depends(get_db),
):
    """AI 根据归因分析+工作台预测数据自动生成推荐模板"""
    from app.script.models import ReferenceVideo
    from app.published.models import PublishedVideo
    from sqlalchemy import select as _sel
    import json, httpx

    refs = (await db.execute(_sel(ReferenceVideo).limit(100))).scalars().all()
    pub_refs = (await db.execute(_sel(PublishedVideo).limit(50))).scalars().all()
    if len(refs) < 1:
        raise HTTPException(400, "至少需要1个参考视频")

    ref_features = []
    for r in refs:
        af = r.audio_features or {}
        ar = r.analysis_report or {}
        bgm = "轻快" if (af.get("lightness_score") or 0) >= 55 else "稳重"
        ref_features.append({
            "style": r.style or "", "hook": (r.hook_method or "")[:12],
            "bgm": bgm, "rhythm": r.rhythm or 0,
            "hook_quality": ar.get("hook_quality", 0) if isinstance(ar, dict) else 0,
            "pacing_score": ar.get("pacing_score", 0) if isinstance(ar, dict) else 0,
            "engagement_strength": ar.get("engagement_strength", 0) if isinstance(ar, dict) else 0,
            "cta_clarity": ar.get("cta_clarity", 0) if isinstance(ar, dict) else 0,
            "overall_score": ar.get("overall_score", 0) if isinstance(ar, dict) else 0,
            "lightness_score": af.get("lightness_score", 0) or 0,
            "bpm": af.get("bpm", 0) or 0, "play_count": r.play_count or 2000,
        })
    ref_features.sort(key=lambda x: x["play_count"], reverse=True)
    best_refs = ref_features[:3]

    pub_features = []
    for p in pub_refs:
        af = p.audio_features or {}
        ar = p.analysis_report or {}
        bgm = "轻快" if (af.get("lightness_score") or 0) >= 55 else "稳重"
        pub_features.append({
            "title": p.title or "", "style": p.style or "", "hook": (p.hook_method or "")[:12],
            "bgm": bgm, "rhythm": p.rhythm or 0, "play_count": p.play_count or 2000,
            "hook_quality": ar.get("hook_quality", 0) if isinstance(ar, dict) else 0,
            "overall_score": ar.get("overall_score", 0) if isinstance(ar, dict) else 0,
        })
    pub_features.sort(key=lambda x: x["play_count"], reverse=True)
    best_pubs = pub_features[:3]

    ref_desc = "\n".join([f"  风格={f['style']} Hook={f['hook']} BGM={f['bgm']} 节奏={f['rhythm']}s 播放量={f['play_count']} Hook质量={f['hook_quality']} 综合评分={f['overall_score']}" for f in best_refs])
    pub_desc = "\n".join([f"  标题={f['title']} 风格={f['style']} Hook={f['hook']} BGM={f['bgm']} 播放量={f['play_count']}" for f in best_pubs]) if best_pubs else "  暂无已生成视频"

    prompt = f"""你是一个电商短视频策略专家。根据以下数据生成3个高质量可执行的灵感模板。

【参考视频最佳组合（按实际播放量排序）】
{ref_desc}

【已生成视频数据】
{pub_desc}

分析要求：
1. 参考视频的"播放量"是真实数据
2. 找出高播放量组合的共同特征（风格、Hook、BGM、节奏）
3. 生成的模板要具体、可执行

请输出JSON数组（不要其他文本）：
[
  {{
    "name": "模板名称（简短有力）",
    "strategy": "创作策略描述（包含风格选择、Hook手法、BGM建议、节奏把控等完整策略说明）",
    "factors": {{
      "hook": {{"type": "Hook手法", "description": "具体开场方式"}},
      "scene": {{"type": "场景设计", "description": "画面和场景安排"}},
      "narration": {{"type": "旁白策略", "description": "旁白/台词风格"}},
      "visual": {{"type": "画面风格", "description": "视觉风格和特效"}},
      "ending": {{"type": "结尾CTA", "description": "引导转化方式"}}
    }},
    "category": "适用品类（食品/美妆/家电/服饰等）",
    "tags": ["标签1", "标签2", "标签3"],
    "attribution_score": 0-100的整数（基于数据评估的推荐强度）
  }}
]

要求：
1. 模板要具体可执行，不能太抽象
2. 每个模板聚焦一个不同的风格方向
3. attribution_score 反映该模板被数据支持的强度"""

    wf_cfg = None
    try:
        from app.workflow.models import WorkflowConfig
        from sqlalchemy import select as _s
        q = _s(WorkflowConfig).where(
            WorkflowConfig.workflow_name == "material-analyze",
            WorkflowConfig.enabled == 1,
        ).limit(1)
        wf_cfg = (await db.execute(q)).scalar_one_or_none()
    except Exception as e:
        print(f"[ai-generate] workflow query: {e}")
    if not wf_cfg:
        return _build_fallback_templates(best_refs)

    cfg = json.loads(wf_cfg.config or "{}")
    api_key = cfg.get("api_key")
    base_url = (cfg.get("base_url") or "https://api.deepseek.com/v1").rstrip("/")
    model = cfg.get("model", "deepseek-v4-flash")

    try:
        payload = {
            "model": model, "temperature": 0.7,
            "messages": [
                {"role": "system", "content": "你是电商短视频策略专家，输出结构化JSON。"},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{base_url}/chat/completions", json=payload,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
            if resp.status_code == 200:
                c = resp.json()["choices"][0]["message"]["content"]
                parsed = json.loads(c)
                templates = parsed if isinstance(parsed, list) else parsed.get("templates", [parsed])
                return {"templates": templates, "source": "ai"}
    except Exception as e:
        print(f"[ai-generate] LLM failed: {e}")

    return _build_fallback_templates(best_refs)


@router.post("/templates/optimize-prompt")
async def optimize_template_prompt(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """根据归因分析优化指定模板的 Prompt（system.md）"""
    template_name = body.get("template_name", "")
    current_content = body.get("content", "")
    from app.script.models import ReferenceVideo
    from app.published.models import PublishedVideo
    from sqlalchemy import select as _sel
    import json, httpx

    refs = (await db.execute(_sel(ReferenceVideo).limit(100))).scalars().all()
    pubs = (await db.execute(_sel(PublishedVideo).limit(50))).scalars().all()

    combo_counts = {}
    for r in refs:
        af = r.audio_features or {}
        bgm = "轻快" if (af.get("lightness_score") or 0) >= 55 else "稳重"
        key = (r.style or "?", (r.hook_method or "")[:8], bgm)
        combo_counts[key] = combo_counts.get(key, 0) + 1
    best_combos = sorted(combo_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    combo_text = "; ".join([f"{s}/{h}/{b}" for (s, h, b), _ in best_combos])

    tpl_pubs = [p for p in pubs if (p.script_template or "") == template_name]
    pub_count = len(tpl_pubs)
    avg_play = round(sum(p.play_count or 2000 for p in tpl_pubs) / pub_count) if pub_count else 0

    wf_cfg = None
    try:
        from app.workflow.models import WorkflowConfig
        from sqlalchemy import select as _s
        wf_cfg = (await db.execute(
            _s(WorkflowConfig).where(
                WorkflowConfig.workflow_name == "material-analyze",
                WorkflowConfig.enabled == 1
            ).limit(1)
        )).scalar_one_or_none()
    except: pass

    if wf_cfg:
        cfg = json.loads(wf_cfg.config or "{}")
        api_key = cfg.get("api_key")
        base_url = (cfg.get("base_url") or "https://api.deepseek.com/v1").rstrip("/")
        model = cfg.get("model", "deepseek-v4-flash")

        prompt = f"""你是一个电商短视频Prompt优化专家。根据以下数据和分析，优化该剧本模板的system.md。

【当前模板名称】
{template_name}

【当前Prompt内容】
{current_content[:2000]}

【归因分析数据】
高播放量组合：{combo_text}
模板使用次数：{pub_count}次，平均播放量：{avg_play}

优化要求：
1. 保留原始Prompt的核心结构和意图
2. 根据归因数据调整策略方向（风格、Hook手法、节奏等）
3. 融入高播放量组合的要素
4. 输出优化后的完整system.md内容

请只输出优化后的Prompt内容，不要解释。"""

        try:
            payload = {
                "model": model, "temperature": 0.6,
                "messages": [
                    {"role": "system", "content": "你是电商短视频Prompt优化专家。只输出优化后的Prompt内容。"},
                    {"role": "user", "content": prompt},
                ],
            }
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(f"{base_url}/chat/completions", json=payload,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
                if resp.status_code == 200:
                    optimized = resp.json()["choices"][0]["message"]["content"].strip()
                    return {"source": "ai", "optimized_content": optimized}
        except Exception as e:
            print(f"[optimize-prompt] LLM failed: {e}")

    return {"source": "data", "optimized_content": current_content, "message": "LLM不可用，返回原始内容"}


def _build_fallback_templates(best: list) -> dict:
    """LLM不可用时，基于数据硬编码模板"""
    templates = []
    for i, f in enumerate(best[:3]):
        templates.append({
            "name": f"{f['style']}+{f['hook']}模板",
            "strategy": f"采用{f['style']}风格，{f['hook']}手法开场，配合{f['bgm']}背景音乐，节奏控制在{f['rhythm']}秒/镜左右。参考高播放量视频的策略。",
            "factors": {
                "hook": {"type": f["hook"], "description": f"以{f['hook']}方式开场，前3秒抓住注意力"},
                "scene": {"type": "场景串联", "description": "2-3个场景快速切换，保持节奏紧凑"},
                "narration": {"type": "旁白配合", "description": "简洁有力的旁白配合画面节奏"},
                "visual": {"type": f["style"], "description": f"采用{f['style']}的视觉风格和剪辑手法"},
                "ending": {"type": "CTA引导", "description": "结尾明确引导用户行动"},
            },
            "category": "通用",
            "tags": [f["style"], f["hook"], f["bgm"]],
            "attribution_score": 85 - i * 5,
        })
    return {"templates": templates, "source": "data"}
