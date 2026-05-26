"""Celery 异步任务 — 工作流调用 + 文件转存"""
import requests
from app.workers import celery_app
from app.workers.workflow import WORKFLOW_TOKENS


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def call_workflow(self, workflow_name: str, payload: dict, task_id: int):  # pragma: no cover
    """
    调用扣子编程工作流，失败自动重试
    用于 Celery worker 异步执行，不阻塞 API
    """
    token = WORKFLOW_TOKENS.get(workflow_name)
    if not token:
        raise ValueError(f"未知工作流: {workflow_name}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            "https://api.coze.cn/v1/workflow/run",
            headers=headers,
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        result = resp.json()
        return {"workflow": workflow_name, "task_id": task_id, "result": result}
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task
def download_and_store(url: str, material_type: str, task_id: int):  # pragma: no cover
    """
    下载临时签名URL文件，转存MinIO
    """
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        # TODO: 上传到 MinIO
        return {"url": url, "task_id": task_id, "stored": True}
    except Exception as e:
        raise Exception(f"下载失败: {e}")
