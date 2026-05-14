"""Purchase Order Repository."""
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select, update as sa_update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models.db_models import PurchaseOrder, POStatus
from app.repositories.base_repository import BaseRepository


class PurchaseOrderRepository(BaseRepository[PurchaseOrder]):
    def __init__(self, session: AsyncSession):
        super().__init__(PurchaseOrder, session)

    async def get_by_id_with_items(self, po_id: uuid.UUID) -> Optional[PurchaseOrder]:
        result = await self.session.execute(
            select(PurchaseOrder)
            .options(selectinload(PurchaseOrder.line_items))
            .where(PurchaseOrder.id == po_id, PurchaseOrder.is_deleted == False)
        )
        return result.scalar_one_or_none()

    async def get_by_po_number(self, po_number: str) -> Optional[PurchaseOrder]:
        result = await self.session.execute(
            select(PurchaseOrder).where(PurchaseOrder.po_number == po_number)
        )
        return result.scalar_one_or_none()

    async def get_by_requester(
        self, requester_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> List[PurchaseOrder]:
        result = await self.session.execute(
            select(PurchaseOrder)
            .where(
                PurchaseOrder.requester_id == requester_id,
                PurchaseOrder.is_deleted == False,
            )
            .offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_pending_approvals(self) -> List[PurchaseOrder]:
        result = await self.session.execute(
            select(PurchaseOrder).where(PurchaseOrder.status == POStatus.PENDING_APPROVAL)
        )
        return list(result.scalars().all())

    async def update(
        self, entity_id: uuid.UUID, obj_in: Dict[str, Any]
    ) -> Optional[PurchaseOrder]:
        """
        Override CRÍTICO v5: el BaseRepository.update() llama a get_by_id()
        simple (sin selectinload), lo que causa MissingGreenlet al serializar
        la response que incluye line_items en todos los endpoints de transición
        (submit / approve / reject / cancel).

        Esta versión usa get_by_id_with_items() para que siempre devuelva
        la OC con sus line_items ya hidratados.
        """
        await self.session.execute(
            sa_update(PurchaseOrder)
            .where(PurchaseOrder.id == entity_id)
            .values(**obj_in)
        )
        # Refresh con eager-load para evitar lazy-loading en contexto async
        return await self.get_by_id_with_items(entity_id)
