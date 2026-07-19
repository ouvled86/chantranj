"""Celery application — Redis broker; review/analysis tasks arrive in Phase 5."""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery = Celery("the_study", broker=settings.redis_url)
celery.conf.task_default_queue = "default"
celery.conf.broker_connection_retry_on_startup = True
celery.conf.imports = ("app.workers.tasks",)


@celery.task(name="ops.ping")
def ping() -> str:
    """Smoke-test task: `celery call ops.ping` should return 'pong'."""
    return "pong"
