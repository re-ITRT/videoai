"""
优质视频库 - API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.deps import get_current_user
from app.auth.models import User
from .schemas import (
    VideoAnalyzeRequest,
    VideoAnalyzeResponse,
    ReferenceVideoResponse,
    ReferenceVideoListResponse,
)
from .service import (
    analyze_and_save_video,
    get_reference_videos,
    get_reference_video_by_id,
    delete_reference_video,
)

router = APIRouter(prefix="/api/v1/reference", tags=["reference"])


@router.post("/upload-analyze")
async def upload_and_analyze(
    file: UploadFile = File(None),
    source_url: str = Form(None),
    title: str = Form(None),
    category: str = Form(None),
    source_platform: str = Form("custom"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传视频 → material-embed提取scenes → video-analyze语义分析 → 存库"""
    import os, uuid, shutil, json, httpx
    from app.core.signer import generate_signed_url
    from app.workers.workflow import call_workflow
    from app.script.models import ReferenceVideo

    saved_url = None
    if file and file.filename:
        ext = os.path.splitext(file.filename)[1] or ".mp4"
        fname = f"{uuid.uuid4().hex}{ext}"
        fpath = f"/app/uploads/analyze/{fname}"
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, "wb") as f:
            shutil.copyfileobj(file.file, f)
        saved_url = generate_signed_url(fpath.replace("/app/uploads", "/uploads"), expire_seconds=86400)
        saved_url = f"http://114.117.242.17:3000{saved_url}"

    video_url = saved_url or source_url or ""

    # 判断是否视频文件
    is_video = False
    if file and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        is_video = ext in (".mp4", ".mov", ".avi", ".webm", ".mkv")
    elif source_url:
        is_video = any(source_url.lower().endswith(e) for e in (".mp4", ".mov", ".avi", ".webm"))

    # 视频太大？压缩一份给 Coze（本地保留原片）
    embed_video_url = video_url
    if saved_url and is_video:
        import subprocess, os
        size_mb = os.path.getsize(fpath) / (1024 * 1024)
        if size_mb > 2.8:
            compressed = fpath.replace(".mp4", "_coze.mp4").replace(".mov", "_coze.mp4")
            subprocess.run(
                ["ffmpeg", "-i", fpath, "-vf", "scale=min(720,iw):min(1280,ih)", "-b:v", "700K", "-c:a", "aac", "-b:a", "64K", "-y", compressed],
                capture_output=True, text=True, timeout=60,
            )
            if os.path.exists(compressed):
                # 用压缩版 URL 给 Coze
                signed2 = generate_signed_url(compressed.replace("/app/uploads", "/uploads"), expire_seconds=86400)
                embed_video_url = f"http://114.117.242.17:3000{signed2}"
                print(f"[upload-analyze] compressed for Coze: {size_mb:.1f}MB -> {os.path.getsize(compressed)/(1024*1024):.1f}MB")

    # 视频截取第一帧作为封面
    cover_url = ""
    if saved_url and is_video:
        import subprocess
        cover_name = f"cover_{uuid.uuid4().hex}.jpg"
        cover_path = f"/app/uploads/analyze/{cover_name}"
        subprocess.run(
            ["ffmpeg", "-i", fpath, "-vframes", "1", "-q:v", "2", "-y", cover_path],
            capture_output=True, text=True, timeout=30,
        )
        if os.path.exists(cover_path):
            cover_url = f"http://114.117.242.17:3000/uploads/analyze/{cover_name}"

    embed_data = {}
    scenes = []
    tags = []

    # ── 本地 LLM 素材分析（替代 Coze 工作流）──┐
    local_tags = []
    local_text_content = ""
    local_scenes = []
    local_analyze = {}
    try:
        from app.workflow.models import WorkflowConfig
        from sqlalchemy import select as _s
        wf = await db.execute(_s(WorkflowConfig).where(
            WorkflowConfig.user_id == user.id,
            WorkflowConfig.workflow_name == "material-analyze",
            WorkflowConfig.enabled == 1,
        ))
        wf_cfg = wf.scalar_one_or_none()
        if wf_cfg:
            cfg_dict = json.loads(wf_cfg.config or "{}")
            api_key = cfg_dict.get("api_key")
            base_url = (cfg_dict.get("base_url") or "https://api.deepseek.com/v1").rstrip("/")
            model = cfg_dict.get("model", "deepseek-v4-flash")
            if api_key and video_url:
                llm_prompt = f"""分析以下视频/图片内容，以JSON格式输出（不要其他文本）：
{{
  "title": "简短标题",
  "description": "详细的多模态内容描述（包含画面、主体、动作、氛围等）",
  "tags": ["标签1", "标签2", ...],
  "scenes": [
    {{"scene_id": 1, "time_range": "<0s-3s>", "description": "场景描述", "script": "旁白/台词"}}
  ],
  "analysis": {{"style": "风格描述", "audience": "目标人群", "mood": "氛围情绪", "hook_quality": 85, "pacing_score": 70, "engagement_strength": 90, "cta_clarity": 60, "overall_score": 78, "formula": "痛点Hook+场景对比+产品特写+CTA", "improvement_suggestions": "建议在前3秒强化视觉冲击力"}}
}}
视频URL：{video_url[:80]}...
标题：{title or "无"}
分类：{category or "无"}"""
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "你是素材内容分析专家，仔细分析视频/图片内容，输出结构化JSON数据，只输出JSON不要其他内容。"},
                        {"role": "user", "content": llm_prompt}
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"},
                }
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(
                        f"{base_url}/chat/completions",
                        json=payload,
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    )
                    if resp.status_code == 200:
                        result = resp.json()
                        content = result["choices"][0]["message"]["content"]
                        import json as _j
                        parsed = _j.loads(content)
                        local_tags = parsed.get("tags", [])
                        local_text_content = parsed.get("description", "")
                        local_scenes = parsed.get("scenes", [])
                        local_analyze = parsed.get("analysis", {})
                        if parsed.get("title"):
                            title = parsed["title"]
    except Exception as e:
        print(f"[upload-analyze] local LLM analyze failed: {e}")

    # 调 material-embed（Coze 兜底）
    try:
        embed_payload = {"material_type": "product"}
        if is_video:
            embed_payload["video_url"] = embed_video_url
            print(f"[upload-analyze] video_url sent to material-embed: {embed_video_url[:80]}")
        else:
            embed_payload["image_url"] = video_url
            embed_payload["brief_description"] = title or "上传素材"
        embed_result = await call_workflow("material-embed", embed_payload)
        embed_data = embed_result.get("data") if isinstance(embed_result, dict) and "data" in embed_result else embed_result
        scenes = embed_data.get("scenes", []) if isinstance(embed_data, dict) else []
        if isinstance(embed_data, dict):
            tags = embed_data.get("video_tags", []) or embed_data.get("tags", [])
    except Exception as e:
        print(f"[upload-analyze] material-embed failed: {e}")
        embed_data = {}
        scenes = []
        tags = []

    # 2. 调 video-analyze（视频用 scenes 分析）
    analyze_result = {}
    if not scenes and video_url:
        scenes = [{"scene_id": 1, "time_range": "<00:00-00:05>", "description": title or "上传的视频素材", "script": ""}]

    if scenes:
        try:
            analyze_result = await call_workflow("video-analyze", {
                "scenes": scenes,
                "source_platform": source_platform,
                "title": title or "",
                "category": category or "",
            })
            # 合并 tags（material-embed + video-analyze）
            analyze_tags = analyze_result.get("tags", []) if isinstance(analyze_result, dict) else []
            if analyze_tags:
                merged = list(dict.fromkeys(tags + analyze_tags))
                tags = merged
        except Exception:
            analyze_result = {}

    scenes = local_scenes or scenes or []
    tags = local_tags or tags or []
    text_content = local_text_content or (embed_data.get("text_content", "") if isinstance(embed_data, dict) else "")
    # 计算平均场景时长（节奏）
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

    # ── 自动音频分析（Librosa）───
    audio_features = {}
    if saved_url and is_video and os.path.exists(fpath):
        import subprocess, tempfile, numpy as np
        tmpdir = tempfile.mkdtemp()
        try:
            audio_path = os.path.join(tmpdir, "audio.wav")
            subprocess.run(
                ["ffmpeg", "-i", fpath, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-y", audio_path],
                capture_output=True, text=True, timeout=120,
            )
            if os.path.exists(audio_path):
                import librosa
                y, sr = librosa.load(audio_path, sr=None, mono=True)
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
                print(f"[upload-analyze] audio: {mood}({lightness}) BPM={bpm}")
        except Exception as e:
            print(f"[upload-analyze] audio analysis failed: {e}")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    db_video = ReferenceVideo(
        user_id=str(current_user.id),
        source_platform=source_platform,
        source_url=video_url,
        title=title or (embed_data.get("text_content", "")[:30] if isinstance(embed_data, dict) else ""),
        category=category,
        # material-embed 数据
        tags=tags,
        text_content=text_content,
        text_embedding=embed_data.get("text_embedding", []) if isinstance(embed_data, dict) else [],
        image_embedding=embed_data.get("image_embedding", []) if isinstance(embed_data, dict) else [],
        scenes=scenes,
        cover_url=cover_url,
        rhythm=rhythm,
        # video-analyze 数据
        hook_method=analyze_result.get("hook_method", ""),
        selling_points=analyze_result.get("selling_points", []),
        storyboard=analyze_result.get("storyboard", []),
        style=analyze_result.get("style", ""),
        analysis_report=local_analyze if local_analyze else (analyze_result or {}),
        audio_features=audio_features,
    )
    db.add(db_video)
    await db.commit()
    await db.refresh(db_video)

    return {"success": True, "video_id": db_video.id, "message": f"嵌入完成({len(scenes)} scenes) + 分析完成"}


@router.get("/videos", response_model=ReferenceVideoListResponse)
async def list_reference_videos(
    category: Optional[str] = Query(None),
    style: Optional[str] = Query(None),
    source_platform: Optional[str] = Query(None),
    tag: Optional[str] = Query(None, description="按标签筛选"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total, videos = await get_reference_videos(
        db, str(current_user.id), category, style, source_platform, tag, skip, limit
    )
    
    return ReferenceVideoListResponse(
        total=total,
        items=[ReferenceVideoResponse.model_validate(v) for v in videos],
    )


@router.get("/tags")
async def list_tags(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有标签（去重）"""
    from sqlalchemy import text
    r = await db.execute(text("""
        SELECT DISTINCT jsonb_array_elements_text(tags) as t
        FROM reference_videos
        WHERE user_id = :uid AND tags IS NOT NULL
        ORDER BY t
    """), {"uid": str(current_user.id)})
    tags = [row[0] for row in r if row[0]]
    return {"tags": tags}


@router.get("/videos/{video_id}", response_model=ReferenceVideoResponse)
async def get_video_detail(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个参考视频详情"""
    video = await get_reference_video_by_id(db, video_id, str(current_user.id))
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    
    return ReferenceVideoResponse.model_validate(video)


@router.post("/videos/{video_id}/view")
async def increment_reference_view(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """增加参考视频播放量"""
    from app.script.models import ReferenceVideo
    r = await db.get(ReferenceVideo, video_id)
    if not r or str(r.user_id) != str(current_user.id):
        raise HTTPException(404, "视频不存在")
    r.play_count = (r.play_count or 2000) + 1
    await db.commit()
    return {"play_count": r.play_count}


@router.put("/videos/{video_id}/play-count")
async def update_reference_play_count(
    video_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """设置参考视频播放量"""
    from app.script.models import ReferenceVideo
    r = await db.get(ReferenceVideo, video_id)
    if not r or str(r.user_id) != str(current_user.id):
        raise HTTPException(404, "视频不存在")
    r.play_count = body.get("play_count", 2000)
    await db.commit()
    return {"play_count": r.play_count}


@router.post("/videos/{video_id}/analyze-audio")
async def analyze_reference_audio(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分析参考视频的音频 → 提取 Librosa 特征"""
    from app.script.models import ReferenceVideo
    import subprocess, tempfile, os, shutil, numpy as np

    r = await db.get(ReferenceVideo, video_id)
    if not r or str(r.user_id) != str(current_user.id):
        raise HTTPException(404, "视频不存在")

    # 找到本地视频文件
    video_path = None
    src = str(r.source_url or "")
    if src:
        import re
        # 处理 /signed/xxx/filename 格式
        m = re.search(r'/signed/[^/]+/(.+)', src)
        if m:
            candidate = "/app/uploads/" + m.group(1)
            if os.path.exists(candidate):
                video_path = candidate
        # 处理 /uploads/ 格式
        if not video_path and "/uploads/" in src:
            candidate = "/app" + src[src.find("/uploads/"):]
            if os.path.exists(candidate):
                video_path = candidate
    if not video_path and r.cover_url:
        src2 = str(r.cover_url)
        import re
        m = re.search(r'/signed/[^/]+/(.+)', src2)
        if m:
            for ext in ('.mp4', '.webm', '.mov'):
                trial = re.sub(r'\.\w+$', ext, "/app/uploads/" + m.group(1))
                if os.path.exists(trial):
                    video_path = trial
                    break
    if not video_path:
        raise HTTPException(400, "视频文件不存在，无法分析音频")

    tmpdir = tempfile.mkdtemp()
    try:
        # FFmpeg 提取音频
        audio_path = os.path.join(tmpdir, "audio.wav")
        subprocess.run(
            ["ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-y", audio_path],
            capture_output=True, text=True, timeout=120,
        )
        if not os.path.exists(audio_path):
            raise HTTPException(500, "音频提取失败")

        # Librosa 分析
        import librosa
        y, sr = librosa.load(audio_path, sr=None, mono=True)
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

        r.audio_features = audio_features
        await db.commit()
        return audio_features
    except ImportError:
        raise HTTPException(500, "librosa 未安装")
    except Exception as e:
        raise HTTPException(500, f"音频分析失败: {str(e)}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@router.delete("/videos/{video_id}")
async def delete_video(
    video_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除参考视频"""
    success = await delete_reference_video(db, video_id, str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="视频不存在")
    
    return {"success": True, "message": "删除成功"}
