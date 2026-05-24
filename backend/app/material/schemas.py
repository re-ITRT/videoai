from pydantic import BaseModel
from typing import Optional


class MaterialUploadRequest(BaseModel):
    product_id: Optional[int] = None
    material_type: str  # product / general / reference
    input_type: str  # image / video


class MaterialSearchRequest(BaseModel):
    query: str
    product_id: Optional[int] = None
    threshold: float = 0.6
    max_results: int = 50
    search_level: str = "material"  # material / slice


class MaterialSearchResult(BaseModel):
    id: int
    similarity: float
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    text_content: Optional[str] = None
    tags: list = []
