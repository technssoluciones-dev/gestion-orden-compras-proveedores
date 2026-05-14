"""Approval routes — motor de aprobaciones con RBAC."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.approval_service import ApprovalService
from app.schemas.purchase_order import PurchaseOrderResponse
from app.api.deps import CurrentUser

router = APIRouter()


class RejectBody(BaseModel):
    """Cuerpo para rechazar una OC."""
    reason: str

    model_config = {"json_schema_extra": {"example": {"reason": "Presupuesto insuficiente"}}}


@router.get("/pending", response_model=list[PurchaseOrderResponse])
async def list_pending_approvals(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Lista OCs en PENDING_APPROVAL que el usuario puede gestionar."""
    svc = ApprovalService(db)
    return await svc.get_pending_approvals(current_user)


@router.post("/{po_id}/submit", response_model=PurchaseOrderResponse)
async def submit_for_approval(
    po_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Envía la OC del usuario a aprobación (DRAFT → PENDING_APPROVAL)."""
    svc = ApprovalService(db)
    return await svc.submit_for_approval(po_id, current_user)


@router.post("/{po_id}/approve", response_model=PurchaseOrderResponse)
async def approve_order(
    po_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Aprueba la OC (PENDING_APPROVAL → APPROVED).
    Requiere rol ADMIN, MANAGER, APPROVER o FINANCE.
    Verifica límite de aprobación del usuario.
    """
    svc = ApprovalService(db)
    return await svc.approve(po_id, current_user)


@router.post("/{po_id}/reject", response_model=PurchaseOrderResponse)
async def reject_order(
    po_id: uuid.UUID,
    body: RejectBody,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Rechaza la OC con motivo obligatorio (PENDING_APPROVAL → REJECTED)."""
    svc = ApprovalService(db)
    return await svc.reject(po_id, current_user, body.reason)


@router.post("/{po_id}/cancel", response_model=PurchaseOrderResponse)
async def cancel_order(
    po_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Cancela la OC.
    Solo el solicitante o ADMIN/MANAGER pueden cancelar.
    """
    svc = ApprovalService(db)
    return await svc.cancel(po_id, current_user)
