"""Budget Repository."""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.db_models import Budget, BudgetPeriod
from app.repositories.base_repository import BaseRepository


class BudgetRepository(BaseRepository[Budget]):
    """Repository for Budget model."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Budget, session)

    async def get_active_by_department(
        self, department_id: uuid.UUID
    ) -> List[Budget]:
        """Presupuestos activos de un departamento."""
        result = await self.session.execute(
            select(Budget).where(
                Budget.department_id == department_id,
                Budget.is_active == True,
            )
        )
        return list(result.scalars().all())

    async def get_by_department_and_year(
        self,
        department_id: uuid.UUID,
        fiscal_year: int,
        period: Optional[BudgetPeriod] = None,
    ) -> List[Budget]:
        """Presupuesto de un departamento en un año fiscal."""
        stmt = select(Budget).where(
            Budget.department_id == department_id,
            Budget.fiscal_year == fiscal_year,
            Budget.is_active == True,
        )
        if period:
            stmt = stmt.where(Budget.period == period)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
