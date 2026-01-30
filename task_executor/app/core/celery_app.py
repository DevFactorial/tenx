from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "workflow_executor",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.services.worker"]
)

# Use settings for dynamic queue routing
celery_app.conf.update(
    task_routes={
        "worker.execute_script": {"queue": settings.CELERY_QUEUE_NAME}
    },
    # Optional: ensure timestamps are consistent
    task_track_started=True,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)