"""
ProcureFlow AI — Audit Service

Escribe eventos de negocio al modelo AuditLog.
Conecta con auth_service y purchase_order_service.

Uso:
    audit = AuditService(db)
    await audit.log(
        user_id=current_user.id,
        action="po.submit",
        entity_type="PurchaseOrder",
        entity_id=str(po.id),
        new_values={"status": "pending_approval"},
    )
"""
import uuid
from typing import Any, Dict, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.db_models import AuditLog

logger = structlog.get_logger(__name__)


class AuditService:
    """Writes structured audit events to the audit_logs table."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log(
        self,
        action: str,
        entity_type: str,
        user_id: Optional[uuid.UUID] = None,
        entity_id: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Persist an audit event.

        Args:
            action:       Dot-notation action name, e.g. "po.submit", "auth.login".
            entity_type:  Model name, e.g. "PurchaseOrder", "Vendor", "User".
            user_id:      Actor UUID (None for system events).
            entity_id:    Target entity's UUID as string.
            old_values:   Snapshot before mutation.
            new_values:   Snapshot after mutation.
            ip_address:   Client IP from request.
            user_agent:   Client User-Agent header.
            request_id:   Correlation ID from X-Request-ID header.
        """
        entry = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
        self.session.add(entry)
        await self.session.flush()

        logger.info(
            "audit_event",
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=str(user_id) if user_id else None,
        )
        return entry

    async def log_login(
        self,
        user_id: uuid.UUID,
        email: str,
        ip_address: Optional[str] = None,
        success: bool = True,
    ) -> AuditLog:
        """Convenience: log an authentication event."""
        return await self.log(
            action="auth.login" if success else "auth.login_failed",
            entity_type="User",
            user_id=user_id if success else None,
            entity_id=str(user_id) if success else None,
            new_values={"email": email, "success": success},
            ip_address=ip_address,
        )

    async def log_po_transition(
        self,
        user_id: uuid.UUID,
        po_id: str,
        from_status: str,
        to_status: str,
        reason: Optional[str] = None,
    ) -> AuditLog:
        """Convenience: log a purchase-order status transition."""
        return await self.log(
            action=f"po.{to_status.lower()}",
            entity_type="PurchaseOrder",
            user_id=user_id,
            entity_id=po_id,
            old_values={"status": from_status},
            new_values={"status": to_status, "reason": reason},
        )

    async def log_vendor_change(
        self,
        user_id: uuid.UUID,
        vendor_id: str,
        action: str,
        changes: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Convenience: log a vendor CRUD event."""
        return await self.log(
            action=f"vendor.{action}",
            entity_type="Vendor",
            user_id=user_id,
            entity_id=vendor_id,
            new_values=changes,
        )
