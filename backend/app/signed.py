"""签名URL路由 — 验证token后返回文件"""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.core.signer import verify_signed_url

UPLOAD_DIR = Path("/app/uploads")
router = APIRouter(tags=["signed"])


@router.get("/signed/{token}/{filename}")
async def serve_signed_file(token: str, filename: str):
    """验证签名token后返回文件"""
    if not verify_signed_url(token, filename):
        raise HTTPException(status_code=403, detail="签名无效或已过期")

    filepath = UPLOAD_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(filepath)
