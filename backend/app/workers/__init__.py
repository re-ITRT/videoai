"""
Workers package - Celery tasks and workflow integration
"""
try:
    from celery import Celery
    from app.config import settings

    celery_app = Celery(
        "video_ai",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.REDIS_URL,
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Asia/Shanghai",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
    )  # pragma: no cover
except ImportError:  # pragma: no cover
    # Celery not installed, but workflow.py still works
    pass
