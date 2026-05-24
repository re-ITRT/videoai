from app.workers import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def call_workflow(self, workflow_name: str, payload: dict, task_id: int):
    """调用扣子编程工作流，失败自动重试"""
    # TODO: implement HTTP call to webhook
    pass


@celery_app.task
def download_and_store(url: str, material_type: str, task_id: int):
    """下载临时签名URL文件，转存MinIO"""
    # TODO: implement download + MinIO upload
    pass
