from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/v1/materials", tags=["materials"])


@router.post("/upload")
async def upload_material():
    """上传素材（触发material-embed工作流）"""
    pass


@router.get("")
async def list_materials():
    """素材列表"""
    pass


@router.post("/search")
async def search_materials():
    """语义检索（material-search嵌入→PG阈值筛选）"""
    pass


@router.delete("/{material_id}")
async def delete_material(material_id: int):
    """删除素材"""
    pass
