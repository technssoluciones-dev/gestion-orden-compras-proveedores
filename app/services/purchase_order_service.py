"""Purchase Order Service — core business logic."""
import uuid
import shortuuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.purchase_order_repository import PurchaseOrderRepository
from app.domain.models.db_models import PurchaseOrder, POLineItem, POStatus
from app.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderResponse
from app.core.exceptions import EntityNotFoundException, InvalidStatusTransitionException
import structlog

logger = structlog.get_logger(__name__)

# Valid status state machine
VALID_TRANSITIONS = {
    POStatus.DRAFT: [POStatus.PENDING_APPROVAL, POStatus.CANCELLED],
    POStatus.PENDING_APPROVAL: [POStatus.APPROVED, POStatus.REJECTED, POStatus.CANCELLED],
    POStatus.APPROVED: [POStatus.ORDERED, POStatus.CANCELLED],
    POStatus.ORDERED: [POStatus.PARTIALLY_RECEIVED, POStatus.RECEIVED],
    POStatus.PARTIALLY_RECEIVED: [POStatus.RECEIVED],
    POStatus.RECEIVED: [POStatus.CLOSED],
    POStatus.REJECTED: [POStatus.DRAFT],
    POStatus.CANCELLED: [],
    POStatus.CLOSED: [],
}


class PurchaseOrderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PurchaseOrderRepository(session)

    def _generate_po_number(self) -> str:
        year = datetime.now(timezone.utc).year
        return f"PO-{year}-{shortuuid.ShortUUID().random(length=8).upper()}"

    def _calculate_totals(self, line_items: List[POLineItem]) -> dict:
        subtotal = sum(item.quantity * item.unit_price for item in line_items)
        tax = subtotal * Decimal("0.19")  # 19% IVA Chile / configurable
        return {
            "subtotal": subtotal,
            "tax_amount": tax,
            "total_amount": subtotal + tax,
        }

    async def create(self, data: PurchaseOrderCreate, requester_id: uuid.UUID) -> PurchaseOrder:
        po_number = self._generate_po_number()
        # Retry once on collision (extremely rare with shortuuid)
        if await self.repo.get_by_po_number(po_number):
            po_number = self._generate_po_number()

        line_items = [
            POLineItem(
                line_number=item.line_number,
                description=item.description,
                quantity=item.quantity,
                unit=item.unit,
                unit_price=item.unit_price,
                total_price=item.quantity * item.unit_price,
                product_code=item.product_code,
                category=item.category,
                notes=item.notes,
            )
            for item in data.line_items
        ]

        totals = self._calculate_totals(line_items)

        po = await self.repo.create({
            "po_number": po_number,
            "title": data.title,
            "description": data.description,
            "priority": data.priority,
            "vendor_id": data.vendor_id,
            "department_id": data.department_id,
            "budget_id": data.budget_id,
            "required_by": data.required_by,
            "currency": data.currency,
            "notes": data.notes,
            "requester_id": requester_id,
            **totals,
        })
        # repo.create() calls flush() — po.id is now available

        for item in line_items:
            item.purchase_order_id = po.id
            self.session.add(item)

        # Explicit flush to assign IDs to line items before response serialization
        await self.session.flush()

        logger.info(
            "purchase_order_created",
            po_id=str(po.id),
            po_number=po_number,
            requester=str(requester_id),
            line_items=len(line_items),
        )
        return await self.get_by_id(po.id)

    async def get_by_id(self, po_id: uuid.UUID) -> PurchaseOrder:
        po = await self.repo.get_by_id_with_items(po_id)
        if not po:
            raise EntityNotFoundException("PurchaseOrder", po_id)
        return po

    async def list_by_requester(
        self,
        requester_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[PurchaseOrder]:
        return await self.repo.get_by_requester(requester_id, skip, limit)

    async def transition_status(
        self,
        po_id: uuid.UUID,
        new_status: POStatus,
        reason: Optional[str] = None,
    ) -> PurchaseOrder:
        po = await self.get_by_id(po_id)
        if new_status not in VALID_TRANSITIONS.get(po.status, []):
            raise InvalidStatusTransitionException(
                "PurchaseOrder", po.status.value, new_status.value
            )
        update_data: dict = {"status": new_status}
        if reason:
            update_data["rejection_reason"] = reason
        if new_status == POStatus.ORDERED:
            update_data["ordered_at"] = datetime.now(timezone.utc)
        if new_status == POStatus.RECEIVED:
            update_data["received_at"] = datetime.now(timezone.utc)

        updated = await self.repo.update(po_id, update_data)
        logger.info(
            "po_status_transition",
            po_id=str(po_id),
            from_status=po.status.value,
            to_status=new_status.value,
        )
        return updated

    async def submit_for_approval(self, po_id: uuid.UUID) -> PurchaseOrder:
        return await self.transition_status(po_id, POStatus.PENDING_APPROVAL)

    async def approve(self, po_id: uuid.UUID) -> PurchaseOrder:
        return await self.transition_status(po_id, POStatus.APPROVED)

    async def reject(self, po_id: uuid.UUID, reason: str) -> PurchaseOrder:
        return await self.transition_status(po_id, POStatus.REJECTED, reason)

    async def cancel(self, po_id: uuid.UUID) -> PurchaseOrder:
        return await self.transition_status(po_id, POStatus.CANCELLED)
