"""
Celery Beat schedule — tareas periódicas.
Agregar a celery_app.py o importar desde aquí.
"""
from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    # Verificar aprobaciones vencidas cada hora
    "check-approval-timeouts": {
        "task": "app.workers.tasks.check_approval_timeouts",
        "schedule": crontab(minute=0),  # cada hora en punto
    },
    # Limpiar registros soft-deleted cada domingo a las 2am
    "cleanup-soft-deleted": {
        "task": "app.workers.tasks.cleanup_soft_deleted_records",
        "schedule": crontab(hour=2, minute=0, day_of_week="sunday"),
        "kwargs": {"days_old": 30},
    },
}
