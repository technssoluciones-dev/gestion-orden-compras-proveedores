"""
ProcureFlow AI — Budget Service
Control presupuestario integrado con creación de OCs.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundException, InsufficientBudgetException
from app.domain.models.db_models import Budget, PurchaseOrder

logger = structlog.get_logger(__name__)


class BudgetService:
    """Verifica y actualiza presupuestos en operaciones de OC."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, budget_id: uuid.UUID) -> Budget:
        """Retorna un presupuesto activo o lanza 404."""
        result = await self.session.execute(
            select(Budget).where(Budget.id == budget_id, Budget.is_active == True)
        )
        budget = result.scalar_one_or_none()
        if not budget:
            raise EntityNotFoundException("Budget", budget_id)
        return budget

    async def check_availability(
        self,
        budget_id: uuid.UUID,
        amount: Decimal,
        currency: str = "USD",
    ) -> Budget:
        """
        Verifica que hay suficiente presupuesto disponible.

        Raises:
            InsufficientBudgetException: Si el monto supera el disponible.
        """
        budget = await self.get_by_id(budget_id)
        available = budget.total_amount - budget.committed_amount
        if amount > available:
            raise InsufficientBudgetException(
                requested=float(amount),
                available=float(available),
                currency=currency,
            )
        return budget

    async def commit_amount(
        self,
        budget_id: uuid.UUID,
        amount: Decimal,
    ) -> Budget:
        """
        Reserva (compromete) un monto del presupuesto al enviar la OC
        a aprobación. No modifica spent_amount hasta que se marca RECEIVED.
        """
        budget = await self.get_by_id(budget_id)
        new_committed = budget.committed_amount + amount
        if new_committed > budget.total_amount:
            raise InsufficientBudgetException(
                requested=float(amount),
                available=float(budget.total_amount - budget.committed_amount),
                currency=budget.currency,
            )
        budget.committed_amount = new_committed
        self.session.add(budget)
        await self.session.flush()
        logger.info(
            "budget_committed",
            budget_id=str(budget_id),
            amount=float(amount),
            committed=float(budget.committed_amount),
        )
        return budget

    async def release_amount(
        self,
        budget_id: uuid.UUID,
        amount: Decimal,
    ) -> Budget:
        """
        Libera el monto comprometido cuando la OC es rechazada o cancelada.
        """
        budget = await self.get_by_id(budget_id)
        budget.committed_amount = max(Decimal("0"), budget.committed_amount - amount)
        self.session.add(budget)
        await self.session.flush()
        logger.info("budget_released", budget_id=str(budget_id), amount=float(amount))
        return budget

    async def mark_spent(
        self,
        budget_id: uuid.UUID,
        amount: Decimal,
    ) -> Budget:
        """
        Mueve el monto de committed → spent cuando la OC se marca como RECEIVED.
        """
        budget = await self.get_by_id(budget_id)
        budget.committed_amount = max(Decimal("0"), budget.committed_amount - amount)
        budget.spent_amount = budget.spent_amount + amount
        self.session.add(budget)
        await self.session.flush()
        logger.info("budget_spent", budget_id=str(budget_id), amount=float(amount))
        return budget

    async def list_by_department(self, department_id: uuid.UUID) -> list[Budget]:
        """Lista presupuestos activos de un departamento."""
        result = await self.session.execute(
            select(Budget).where(
                Budget.department_id == department_id,
                Budget.is_active == True,
            )
        )
        return list(result.scalars().all())
