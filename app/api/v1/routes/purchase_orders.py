"""Purchase Order routes."""
import uuid
from typing import List
from fastapi import APIRouter, Depends, status, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.purchase_order_service import PurchaseOrderService
from app.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderResponse
from app.api.deps import CurrentUser

router = APIRouter()


@router.get("", response_model=List[PurchaseOrderResponse])
async def list_my_orders(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Lista las órdenes de compra del usuario autenticado."""
    svc = PurchaseOrderService(db)
    return await svc.list_by_requester(current_user.id, skip, limit)


@router.post("", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    payload: PurchaseOrderCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Crea una nueva OC en estado DRAFT."""
    svc = PurchaseOrderService(db)
    return await svc.create(payload, current_user.id)


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
async def get_purchase_order(
    po_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = PurchaseOrderService(db)
    return await svc.get_by_id(po_id)


@router.post("/{po_id}/submit", response_model=PurchaseOrderResponse)
async def submit_for_approval(
    po_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Envía la OC a aprobación (DRAFT → PENDING_APPROVAL)."""
    svc = PurchaseOrderService(db)
    return await svc.submit_for_approval(po_id)


@router.post("/{po_id}/approve", response_model=PurchaseOrderResponse)
async def approve_order(
    po_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Aprueba la OC (PENDING_APPROVAL → APPROVED)."""
    svc = PurchaseOrderService(db)
    return await svc.approve(po_id)


class RejectRequest(BaseModel):
    reason: str

    model_config = {"json_schema_extra": {"example": {"reason": "Presupuesto insuficiente"}}}


@router.post("/{po_id}/reject", response_model=PurchaseOrderResponse)
async def reject_order(
    po_id: uuid.UUID,
    payload: RejectRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Rechaza la OC con motivo (PENDING_APPROVAL → REJECTED)."""
    svc = PurchaseOrderService(db)
    return await svc.reject(po_id, payload.reason)


@router.post("/{po_id}/cancel", response_model=PurchaseOrderResponse)
async def cancel_order(
    po_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Cancela la OC.
    Válido desde: DRAFT, PENDING_APPROVAL, APPROVED.
    El servicio valida la transición mediante la máquina de estados.
    """
    svc = PurchaseOrderService(db)
    return await svc.cancel(po_id)
