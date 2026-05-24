from pydantic import BaseModel
from typing import Optional


class TaskCreateRequest(BaseModel):
    product_info: dict
    style: Optional[str] = None
    auto_mode: bool = True
    aspect_ratio: str = "9:16"


class TaskApproveScriptRequest(BaseModel):
    script_id: int
    modifications: Optional[dict] = None


class TaskRetryRequest(BaseModel):
    step: Optional[str] = None  # 重试特定步骤
