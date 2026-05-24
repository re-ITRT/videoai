from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/tasks", tags=["creation"])


@router.post("")
async def create_task():
    """创建视频任务"""
    pass


@router.get("/{task_id}")
async def get_task(task_id: int):
    """任务状态查询"""
    pass


@router.get("/{task_id}/logs")
async def get_task_logs(task_id: int):
    """生成过程追踪日志"""
    pass


@router.post("/{task_id}/approve-script")
async def approve_script(task_id: int):
    """手动模式：批准剧本"""
    pass


@router.post("/{task_id}/retry")
async def retry_task(task_id: int):
    """重试失败步骤"""
    pass


@router.post("/{task_id}/regenerate-scene/{scene_id}")
async def regenerate_scene(task_id: int, scene_id: int):
    """分镜级干预：重生成单个分镜"""
    pass


@router.post("/{task_id}/export")
async def export_video(task_id: int):
    """导出视频（多画幅）"""
    pass
