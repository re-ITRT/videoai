from pydantic import BaseModel
from typing import Optional


class ScriptGenerateRequest(BaseModel):
    product_info: dict
    style: Optional[str] = None
    video_style: Optional[str] = None
    target_duration: int = 15
    selected_materials: list = []
    mode: str = "auto"  # auto / imitation / template
    template_id: Optional[int] = None
    reference_video_id: Optional[int] = None
    additional_instructions: Optional[str] = None
    num_variants: int = 1
