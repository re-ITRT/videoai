"""音频分析 — Librosa 特征提取"""
import os, json, tempfile, shutil
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from app.core.deps import get_current_user
from app.auth.models import User

router = APIRouter(prefix="/api/v1/audio", tags=["audio"])


@router.post("/analyze")
async def analyze_audio(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """上传音频文件并提取 Librosa 信号特征"""
    if not file.filename:
        raise HTTPException(400, "文件不能为空")

    ext = os.path.splitext(file.filename or "audio.mp3")[1].lower()
    if ext not in (".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"):
        raise HTTPException(400, f"不支持的音频格式: {ext}，支持 mp3/wav/m4a/ogg/flac/aac")

    tmpdir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmpdir, f"input{ext}")
    try:
        with open(tmp_path, "wb") as f:
            import shutil as _sh
            _sh.copyfileobj(file.file, f)

        # 用 librosa 提取特征
        import librosa
        y, sr = librosa.load(tmp_path, sr=None, mono=True)
        duration = float(librosa.get_duration(y=y, sr=sr))

        # BPM（节拍速度）
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(tempo) if tempo else 120.0

        # 频谱质心（衡量"明亮度"）
        cent = librosa.feature.spectral_centroid(y=y, sr=sr)
        centroid_mean = float(cent.mean())

        # 过零率（衡量"活泼度"）
        zcr = librosa.feature.zero_crossing_rate(y)
        zcr_mean = float(zcr.mean())

        # 频谱滚降点（高频能量占比）
        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
        rolloff_mean = float(rolloff.mean())

        # 梅尔频谱（用于后续可能的情感分类）
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_mean = [float(mfcc[i].mean()) for i in range(13)]

        # ── 轻快/稳重 评分 (0-100) ──
        # 基于 BPM + 频谱质心 + 过零率 加权
        # BPM: 0-60 → 沉稳, 60-120 → 适中, 120+ → 轻快
        bpm_score = min(bpm / 2.0, 50.0)
        # 频谱质心归一化（假设 max ~5000Hz）
        cent_score = min(centroid_mean / 50.0, 25.0)
        # 过零率归一化
        zcr_score = min(zcr_mean * 500, 25.0)
        lightness = round(min(bpm_score + cent_score + zcr_score, 100), 1)

        # 特征标签
        if lightness < 30:
            mood = "稳重"
        elif lightness < 55:
            mood = "中性"
        else:
            mood = "轻快"

        return {
            "filename": file.filename,
            "duration": round(duration, 2),
            "bpm": round(bpm, 1),
            "spectral_centroid": round(centroid_mean, 2),
            "zero_crossing_rate": round(zcr_mean, 6),
            "spectral_rolloff": round(rolloff_mean, 2),
            "mfcc_mean": [round(v, 4) for v in mfcc_mean],
            "lightness_score": lightness,
            "mood": mood,
            "features": {
                "bpm_score": round(bpm_score, 1),
                "centroid_score": round(cent_score, 1),
                "zcr_score": round(zcr_score, 1),
            },
        }
    except ImportError:
        raise HTTPException(500, "librosa 未安装，请运行: pip install librosa")
    except Exception as e:
        raise HTTPException(500, f"音频分析失败: {str(e)}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
