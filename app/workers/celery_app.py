"""Celery app configuration for background tasks."""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "procureflow",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Santiago",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# ── Beat schedule ───────────────────────────────────────────────────────────
# CRÍTICO: importar aquí para que celery beat tenga las tareas periódicas.
# Sin esto, beat arranca vacío y ninguna tarea periódica se ejecuta.
from app.workers.beat_schedule import CELERYBEAT_SCHEDULE  # noqa: E402
celery_app.conf.beat_schedule = CELERYBEAT_SCHEDULE
