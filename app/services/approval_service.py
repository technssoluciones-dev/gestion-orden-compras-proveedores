"""
ProcureFlow AI — Approval Workflow Service
Motor de aprobaciones con RBAC + límites por monto.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AuthorizationException,
    ApprovalLimitExceededException,
    EntityNotFoundException,
    InvalidStatusTransitionException,
)
from app.domain.models.db_models import (
    ApprovalStep,
    ApprovalStatus,
    PurchaseOrder,
    POStatus,
    User,
    UserRole,
)
from app.repositories.purchase_order_repository import PurchaseOrderRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService

logger = structlog.get_logger(__name__)

# Roles que pueden aprobar órdenes de compra
APPROVER_ROLES = {UserRole.ADMIN, UserRole.MANAGER, UserRole.APPROVER, UserRole.FINANCE}


class ApprovalService:
    """Gestiona el ciclo de vida de aprobaciones de OCs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.po_repo = PurchaseOrderRepository(session)
        self.user_repo = UserRepository(session)
        self.audit = AuditService(session)

    async def submit_for_approval(
        self,
        po_id: uuid.UUID,
        requester: User,
    ) -> PurchaseOrder:
        """
        Transición DRAFT → PENDING_APPROVAL.
        Valida que el solicitante es el propietario de la OC.
        """
        po = await self._get_po_or_404(po_id)
        if po.requester_id != requester.id:
            raise AuthorizationException("Solo el solicitante puede enviar su propia OC a aprobación")
        if po.status != POStatus.DRAFT:
            raise InvalidStatusTransitionException("PurchaseOrder", po.status.value, "pending_approval")

        updated = await self.po_repo.update(po_id, {"status": POStatus.PENDING_APPROVAL})
        await self.audit.log_po_transition(
            user_id=requester.id,
            po_id=str(po_id),
            from_status=POStatus.DRAFT.value,
            to_status=POStatus.PENDING_APPROVAL.value,
        )
        logger.info("po_submitted_for_approval", po_id=str(po_id), requester=str(requester.id))
        return updated

    async def approve(
        self,
        po_id: uuid.UUID,
        approver: User,
    ) -> PurchaseOrder:
        """
        Transición PENDING_APPROVAL → APPROVED.

        Validaciones:
        - El aprobador debe tener rol ADMIN, MANAGER, APPROVER o FINANCE.
        - El monto de la OC no puede superar el límite de aprobación del usuario.
        - El aprobador no puede aprobar su propia OC.
        """
        po = await self._get_po_or_404(po_id)

        if po.status != POStatus.PENDING_APPROVAL:
            raise InvalidStatusTransitionException("PurchaseOrder", po.status.value, "approved")

        if approver.role not in APPROVER_ROLES:
            raise AuthorizationException(
                f"El rol '{approver.role.value}' no tiene permisos para aprobar órdenes de compra"
            )

        if po.requester_id == approver.id and approver.role != UserRole.ADMIN:
            raise AuthorizationException("No puedes aprobar tu propia orden de compra")

        approval_limit = Decimal(str(approver.approval_limit)) if approver.approval_limit else Decimal("0")
        if approval_limit > 0 and po.total_amount > approval_limit:
            raise ApprovalLimitExceededException(
                float(po.total_amount),
                float(approval_limit),
            )

        # Registrar paso de aprobación
        step = ApprovalStep(
            id=uuid.uuid4(),
            purchase_order_id=po_id,
            approver_id=approver.id,
            order=1,
            status=ApprovalStatus.APPROVED,
            decision_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            is_current=True,
        )
        self.session.add(step)
        await self.session.flush()

        updated = await self.po_repo.update(po_id, {"status": POStatus.APPROVED})
        await self.audit.log_po_transition(
            user_id=approver.id,
            po_id=str(po_id),
            from_status=POStatus.PENDING_APPROVAL.value,
            to_status=POStatus.APPROVED.value,
        )
        logger.info("po_approved", po_id=str(po_id), approver=str(approver.id))
        return updated

    async def reject(
        self,
        po_id: uuid.UUID,
        approver: User,
        reason: str,
    ) -> PurchaseOrder:
        """Transición PENDING_APPROVAL → REJECTED con motivo obligatorio."""
        po = await self._get_po_or_404(po_id)

        if po.status != POStatus.PENDING_APPROVAL:
            raise InvalidStatusTransitionException("PurchaseOrder", po.status.value, "rejected")

        if approver.role not in APPROVER_ROLES:
            raise AuthorizationException("Rol insuficiente para rechazar órdenes de compra")

        step = ApprovalStep(
            id=uuid.uuid4(),
            purchase_order_id=po_id,
            approver_id=approver.id,
            order=1,
            status=ApprovalStatus.REJECTED,
            decision_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            comments=reason,
            is_current=True,
        )
        self.session.add(step)
        await self.session.flush()

        updated = await self.po_repo.update(po_id, {
            "status": POStatus.REJECTED,
            "rejection_reason": reason,
        })
        await self.audit.log_po_transition(
            user_id=approver.id,
            po_id=str(po_id),
            from_status=POStatus.PENDING_APPROVAL.value,
            to_status=POStatus.REJECTED.value,
            reason=reason,
        )
        logger.info("po_rejected", po_id=str(po_id), reason=reason)
        return updated

    async def cancel(
        self,
        po_id: uuid.UUID,
        actor: User,
    ) -> PurchaseOrder:
        """
        Cancelación desde DRAFT, PENDING_APPROVAL o APPROVED.
        Solo el solicitante o un ADMIN/MANAGER puede cancelar.
        """
        po = await self._get_po_or_404(po_id)

        cancelable = {POStatus.DRAFT, POStatus.PENDING_APPROVAL, POStatus.APPROVED}
        if po.status not in cancelable:
            raise InvalidStatusTransitionException("PurchaseOrder", po.status.value, "cancelled")

        is_owner = po.requester_id == actor.id
        is_privileged = actor.role in {UserRole.ADMIN, UserRole.MANAGER}
        if not is_owner and not is_privileged:
            raise AuthorizationException("Solo el solicitante o un manager puede cancelar esta OC")

        updated = await self.po_repo.update(po_id, {"status": POStatus.CANCELLED})
        await self.audit.log_po_transition(
            user_id=actor.id,
            po_id=str(po_id),
            from_status=po.status.value,
            to_status=POStatus.CANCELLED.value,
        )
        logger.info("po_cancelled", po_id=str(po_id), actor=str(actor.id))
        return updated

    async def get_pending_approvals(self, approver: User) -> list[PurchaseOrder]:
        """Retorna OCs en PENDING_APPROVAL que el aprobador puede gestionar."""
        if approver.role not in APPROVER_ROLES:
            raise AuthorizationException("No tienes permisos para ver aprobaciones pendientes")
        return await self.po_repo.get_pending_approvals()

    async def _get_po_or_404(self, po_id: uuid.UUID) -> PurchaseOrder:
        po = await self.po_repo.get_by_id_with_items(po_id)
        if not po:
            raise EntityNotFoundException("PurchaseOrder", po_id)
        return po
