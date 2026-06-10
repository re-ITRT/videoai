"""
临时签名URL生成 — 用于工作流访问内部文件
"""
import time
import hmac
import hashlib
import base64
from app.config import settings


def generate_signed_url(filepath: str, expire_seconds: int = 31536000) -> str:
    """
    生成临时签名URL
    
    Args:
        filepath: 文件路径，如 /uploads/abc.jpg 或 /uploads/agent_sessions/1/scripts/script_1.json
        expire_seconds: 过期时间（秒），默认1年
    
    Returns:
        签名后的URL路径: /signed/{token}/{relpath}
    """
    expires = int(time.time()) + expire_seconds
    # 取 /uploads/ 之后的相对路径作为标识
    parts = filepath.split("/uploads/")
    relpath = parts[1] if len(parts) > 1 else filepath.split("/")[-1]
    filename = filepath.split("/")[-1]
    
    message = f"{relpath}:{expires}"
    sig = hmac.new(
        settings.SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()[:16]
    
    token = base64.urlsafe_b64encode(f"{sig}:{expires}".encode()).decode().rstrip("=")
    return f"/signed/{token}/{relpath}"


def verify_signed_url(token: str, filename: str) -> bool:
    """
    验证签名URL是否有效且未过期
    """
    try:
        decoded = base64.urlsafe_b64decode(token + "==").decode()
        sig, expires = decoded.split(":")
        expires = int(expires)
    except Exception:
        return False
    
    if time.time() > expires:
        return False
    
    expected = hmac.new(
        settings.SECRET_KEY.encode(),
        f"{filename}:{expires}".encode(),
        hashlib.sha256,
    ).hexdigest()[:16]
    
    return hmac.compare_digest(sig, expected)
