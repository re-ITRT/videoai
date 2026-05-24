from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/scripts", tags=["scripts"])


@router.get("")
async def list_scripts():
    """剧本列表"""
    pass


@router.get("/{script_id}")
async def get_script(script_id: int):
    """剧本详情"""
    pass
