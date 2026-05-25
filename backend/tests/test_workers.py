"""Celery 工作器测试"""
import pytest


class TestWorkerModule:
    """验证 workers 模块可正常导入"""

    def test_import_celery_app(self):
        from app.workers import celery_app
        assert celery_app is not None
        assert celery_app.main == "video_ai"
        assert celery_app.conf.timezone == "Asia/Shanghai"

    def test_call_workflow_task(self):
        from app.workers.tasks import call_workflow
        assert call_workflow is not None
        assert call_workflow.name == "app.workers.tasks.call_workflow"
        assert call_workflow.max_retries == 3

    def test_download_and_store_task(self):
        from app.workers.tasks import download_and_store
        assert download_and_store is not None
        assert download_and_store.name == "app.workers.tasks.download_and_store"
