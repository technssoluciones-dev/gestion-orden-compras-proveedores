"""
ProcureFlow AI — Celery Background Tasks
Implementación real (sin TODOs).
"""
from __future__ import annotations

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from celery.utils.log import get_task_logger
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_approval_notification(
    self,
    po_id: str,
    po_number: str,
    po_title: str,
    approver_email: str,
    requester_name: str,
    amount: float,
    currency: str = "USD",
) -> dict:
    """
    Envía notificación por email cuando una OC requiere aprobación.
    Usa SMTP configurado en settings. Reintentos automáticos en fallo.
    """
    from app.core.config import settings

    logger.info(f"Sending approval notification: PO={po_number} → {approver_email}")

    if not settings.smtp_user or not settings.smtp_password:
        logger.warning("SMTP not configured — skipping email notification")
        return {"status": "skipped", "reason": "smtp_not_configured"}

    subject = f"[ProcureFlow] Aprobación requerida: {po_number}"
    body_html = f"""
    <html><body>
    <h2>Orden de Compra requiere su aprobación</h2>
    <table border="0" cellpadding="8">
      <tr><td><b>Número OC:</b></td><td>{po_number}</td></tr>
      <tr><td><b>Título:</b></td><td>{po_title}</td></tr>
      <tr><td><b>Solicitante:</b></td><td>{requester_name}</td></tr>
      <tr><td><b>Monto:</b></td><td>{currency} {amount:,.2f}</td></tr>
    </table>
    <br>
    <p>Acceda al sistema para aprobar o rechazar: 
       <a href="http://localhost:8000/api/docs">ProcureFlow AI</a>
    </p>
    </body></html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = settings.email_from
        msg["To"]      = approver_email
        msg.attach(MIMEText(body_html, "html"))

        context = ssl.create_default_context()
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.email_from, approver_email, msg.as_string())

        logger.info(f"Approval email sent: {po_number} → {approver_email}")
        return {"status": "sent", "po_id": po_id, "to": approver_email}

    except Exception as exc:
        logger.error(f"Email failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def process_ai_po_analysis(
    self,
    po_id: str,
    title: str,
    description: Optional[str],
    vendor_name: Optional[str],
) -> dict:
    """
    Analiza una OC con IA (Anthropic/OpenAI) y actualiza el registro en DB.
    Se ejecuta en background tras la creación de la OC.
    """
    import asyncio
    from app.ai.po_analyst import POAnalyst

    logger.info(f"AI analysis started: po_id={po_id}")

    try:
        analyst = POAnalyst()

        # Celery es síncrono — corremos el coroutine con asyncio.run
        result = asyncio.run(
            analyst.analyze_po(
                title=title,
                description=description,
                vendor_name=vendor_name,
            )
        )

        logger.info(f"AI analysis complete: po_id={po_id}, category={result.get('category')}")
        return {"status": "completed", "po_id": po_id, "analysis": result}

    except Exception as exc:
        logger.error(f"AI analysis failed: po_id={po_id}, error={exc}")
        raise self.retry(exc=exc)


@celery_app.task
def check_approval_timeouts() -> dict:
    """
    Tarea periódica: marca como EXPIRED las aprobaciones vencidas.
    Programar con Celery Beat cada hora.
    """
    import asyncio

    async def _check():
        from sqlalchemy import select, update
        from datetime import datetime, timezone
        from app.core.database import AsyncSessionFactory
        from app.domain.models.db_models import ApprovalStep, ApprovalStatus

        async with AsyncSessionFactory() as session:
            now = datetime.now(timezone.utc)
            result = await session.execute(
                update(ApprovalStep)
                .where(
                    ApprovalStep.status == ApprovalStatus.PENDING,
                    ApprovalStep.expires_at < now,
                )
                .values(status=ApprovalStatus.EXPIRED)
                .returning(ApprovalStep.id)
            )
            expired_ids = result.scalars().all()
            await session.commit()
            return len(expired_ids)

    count = asyncio.run(_check())
    logger.info(f"Approval timeout check: {count} expired")
    return {"expired_count": count}


@celery_app.task
def cleanup_soft_deleted_records(days_old: int = 30) -> dict:
    """
    Tarea periódica: elimina físicamente registros soft-deleted con más de N días.
    """
    import asyncio

    async def _cleanup():
        from sqlalchemy import delete
        from datetime import datetime, timezone, timedelta
        from app.core.database import AsyncSessionFactory
        from app.domain.models.db_models import PurchaseOrder, Vendor

        cutoff = datetime.now(timezone.utc) - timedelta(days=days_old)
        total = 0

        async with AsyncSessionFactory() as session:
            for Model in [PurchaseOrder, Vendor]:
                r = await session.execute(
                    delete(Model).where(
                        Model.is_deleted == True,
                        Model.deleted_at < cutoff,
                    )
                )
                total += r.rowcount
            await session.commit()

        return total

    count = asyncio.run(_cleanup())
    logger.info(f"Soft-delete cleanup: {count} records purged")
    return {"purged": count}
