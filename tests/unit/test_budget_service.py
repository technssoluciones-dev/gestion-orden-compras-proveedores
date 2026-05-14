"""Unit tests — app/services/budget_service.py"""
from __future__ import annotations

import uuid
import pytest
from decimal import Decimal

from app.domain.models.db_models import Budget, BudgetPeriod, Department
from app.services.budget_service import BudgetService
from app.core.exceptions import InsufficientBudgetException, EntityNotFoundException


async def _make_dept(db_session) -> Department:
    d = Department(
        id=uuid.uuid4(), name="Tech", code=f"T{uuid.uuid4().hex[:4]}", is_active=True
    )
    db_session.add(d)
    await db_session.flush()
    return d


async def _make_budget(db_session, total=Decimal("10000"), committed=Decimal("0")) -> Budget:
    dept = await _make_dept(db_session)
    b = Budget(
        id=uuid.uuid4(),
        name="Q1 Budget",
        department_id=dept.id,
        period=BudgetPeriod.ANNUAL,
        fiscal_year=2026,
        total_amount=total,
        committed_amount=committed,
        spent_amount=Decimal("0"),
        currency="USD",
        is_active=True,
    )
    db_session.add(b)
    await db_session.flush()
    return b


@pytest.mark.asyncio
async def test_check_availability_ok(db_session):
    budget = await _make_budget(db_session, total=Decimal("1000"))
    svc = BudgetService(db_session)
    result = await svc.check_availability(budget.id, Decimal("500"))
    assert result.id == budget.id


@pytest.mark.asyncio
async def test_check_availability_insufficient(db_session):
    budget = await _make_budget(db_session, total=Decimal("100"), committed=Decimal("90"))
    svc = BudgetService(db_session)
    with pytest.raises(InsufficientBudgetException):
        await svc.check_availability(budget.id, Decimal("50"))


@pytest.mark.asyncio
async def test_commit_amount(db_session):
    budget = await _make_budget(db_session, total=Decimal("1000"))
    svc = BudgetService(db_session)
    result = await svc.commit_amount(budget.id, Decimal("300"))
    assert result.committed_amount == Decimal("300")


@pytest.mark.asyncio
async def test_release_amount(db_session):
    budget = await _make_budget(db_session, total=Decimal("1000"), committed=Decimal("500"))
    svc = BudgetService(db_session)
    result = await svc.release_amount(budget.id, Decimal("200"))
    assert result.committed_amount == Decimal("300")


@pytest.mark.asyncio
async def test_mark_spent(db_session):
    budget = await _make_budget(db_session, total=Decimal("1000"), committed=Decimal("500"))
    svc = BudgetService(db_session)
    result = await svc.mark_spent(budget.id, Decimal("300"))
    assert result.spent_amount == Decimal("300")
    assert result.committed_amount == Decimal("200")


@pytest.mark.asyncio
async def test_get_nonexistent_budget_raises(db_session):
    svc = BudgetService(db_session)
    with pytest.raises(EntityNotFoundException):
        await svc.get_by_id(uuid.uuid4())
