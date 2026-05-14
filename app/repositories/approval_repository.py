"""Approval Step Repository."""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.db_models import ApprovalStep, ApprovalStatus
from app.repositories.base_repository import BaseRepository


class ApprovalRepository(BaseRepository[ApprovalStep]):
    """Repository for ApprovalStep model."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ApprovalStep, session)

    async def get_by_po_id(self, po_id: uuid.UUID) -> List[ApprovalStep]:
        """Retorna todos los pasos de aprobación de una OC, ordenados."""
        result = await self.session.execute(
            select(ApprovalStep)
            .where(ApprovalStep.purchase_order_id == po_id)
            .order_by(ApprovalStep.order)
        )
        return list(result.scalars().all())

    async def get_pending_by_approver(
        self, approver_id: uuid.UUID
    ) -> List[ApprovalStep]:
        """Retorna pasos pendientes asignados a un aprobador específico."""
        result = await self.session.execute(
            select(ApprovalStep).where(
                ApprovalStep.approver_id == approver_id,
                ApprovalStep.status == ApprovalStatus.PENDING,
            )
        )
        return list(result.scalars().all())

    async def get_current_step(self, po_id: uuid.UUID) -> Optional[ApprovalStep]:
        """Retorna el paso activo de aprobación de una OC."""
        result = await self.session.execute(
            select(ApprovalStep).where(
                ApprovalStep.purchase_order_id == po_id,
                ApprovalStep.is_current == True,
            )
        )
        return result.scalar_one_or_none()
