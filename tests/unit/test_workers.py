"""Unit tests — app/workers/tasks.py (mock de Celery)."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock


def test_send_approval_notification_no_smtp():
    """Sin SMTP configurado, la tarea retorna status=skipped."""
    from app.workers.tasks import send_approval_notification
    with patch("app.workers.tasks.settings") as mock_settings:
        mock_settings.smtp_user = None
        mock_settings.smtp_password = None
        mock_settings.email_from = "noreply@test.com"
        # run() en Celery no ejecuta async — llamamos la función interna directamente
        result = send_approval_notification.run(
            po_id="po-1",
            po_number="PO-2026-001",
            po_title="Test PO",
            approver_email="approver@test.com",
            requester_name="Requester",
            amount=1000.0,
            currency="USD",
        )
    assert result["status"] == "skipped"
    assert result["reason"] == "smtp_not_configured"


def test_beat_schedule_has_required_tasks():
    """El beat schedule debe contener las tareas periódicas esperadas."""
    from app.workers.beat_schedule import CELERYBEAT_SCHEDULE
    assert "check-approval-timeouts" in CELERYBEAT_SCHEDULE
    assert "cleanup-soft-deleted" in CELERYBEAT_SCHEDULE


def test_celery_app_configuration():
    """La app Celery debe estar configurada con los parámetros correctos."""
    from app.workers.celery_app import celery_app
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
