"""Unit tests — app/services/approval_service.py"""
from __future__ import annotations

import uuid
import pytest
from decimal import Decimal

from app.core.security import hash_password
from app.domain.models.db_models import User, UserRole, PurchaseOrder, POStatus
from app.services.approval_service import ApprovalService
from app.core.exceptions import AuthorizationException, InvalidStatusTransitionException


async def _make_user(db_session, role=UserRole.APPROVER, approval_limit=Decimal("0")) -> User:
    u = User(
        id=uuid.uuid4(),
        email=f"appsvc_{uuid.uuid4().hex[:6]}@test.com",
        username=f"appsvc_{uuid.uuid4().hex[:6]}",
        full_name="Approval Test",
        hashed_password=hash_password("Test1234!"),
        role=role,
        is_active=True,
        is_verified=True,
        approval_limit=approval_limit,
    )
    db_session.add(u)
    await db_session.flush()
    return u


async def _make_po(db_session, requester_id, status=POStatus.DRAFT, total=Decimal("100")) -> PurchaseOrder:
    import shortuuid
    po = PurchaseOrder(
        id=uuid.uuid4(),
        po_number=f"PO-TEST-{shortuuid.uuid()[:6]}",
        title="Test PO",
        status=status,
        priority="normal",
        requester_id=requester_id,
        subtotal=total,
        tax_amount=Decimal("0"),
        discount_amount=Decimal("0"),
        total_amount=total,
        currency="USD",
    )
    db_session.add(po)
    await db_session.flush()
    return po


@pytest.mark.asyncio
async def test_submit_for_approval_success(db_session):
    requester = await _make_user(db_session, UserRole.REQUESTER)
    po = await _make_po(db_session, requester.id, POStatus.DRAFT)
    svc = ApprovalService(db_session)
    result = await svc.submit_for_approval(po.id, requester)
    assert result.status == POStatus.PENDING_APPROVAL


@pytest.mark.asyncio
async def test_submit_by_non_owner_raises(db_session):
    owner = await _make_user(db_session, UserRole.REQUESTER)
    other = await _make_user(db_session, UserRole.REQUESTER)
    po = await _make_po(db_session, owner.id, POStatus.DRAFT)
    svc = ApprovalService(db_session)
    with pytest.raises(AuthorizationException):
        await svc.submit_for_approval(po.id, other)


@pytest.mark.asyncio
async def test_approve_success(db_session):
    requester = await _make_user(db_session, UserRole.REQUESTER)
    approver = await _make_user(db_session, UserRole.APPROVER, Decimal("10000"))
    po = await _make_po(db_session, requester.id, POStatus.PENDING_APPROVAL, Decimal("500"))
    svc = ApprovalService(db_session)
    result = await svc.approve(po.id, approver)
    assert result.status == POStatus.APPROVED


@pytest.mark.asyncio
async def test_approve_exceeds_limit_raises(db_session):
    requester = await _make_user(db_session, UserRole.REQUESTER)
    approver = await _make_user(db_session, UserRole.APPROVER, Decimal("100"))
    po = await _make_po(db_session, requester.id, POStatus.PENDING_APPROVAL, Decimal("5000"))
    svc = ApprovalService(db_session)
    from app.core.exceptions import ApprovalLimitExceededException
    with pytest.raises(ApprovalLimitExceededException):
        await svc.approve(po.id, approver)


@pytest.mark.asyncio
async def test_approve_own_po_raises_for_non_admin(db_session):
    user = await _make_user(db_session, UserRole.APPROVER, Decimal("99999"))
    po = await _make_po(db_session, user.id, POStatus.PENDING_APPROVAL)
    svc = ApprovalService(db_session)
    with pytest.raises(AuthorizationException):
        await svc.approve(po.id, user)


@pytest.mark.asyncio
async def test_reject_success(db_session):
    requester = await _make_user(db_session, UserRole.REQUESTER)
    approver = await _make_user(db_session, UserRole.MANAGER)
    po = await _make_po(db_session, requester.id, POStatus.PENDING_APPROVAL)
    svc = ApprovalService(db_session)
    result = await svc.reject(po.id, approver, "Sin presupuesto")
    assert result.status == POStatus.REJECTED


@pytest.mark.asyncio
async def test_cancel_by_owner_success(db_session):
    requester = await _make_user(db_session, UserRole.REQUESTER)
    po = await _make_po(db_session, requester.id, POStatus.DRAFT)
    svc = ApprovalService(db_session)
    result = await svc.cancel(po.id, requester)
    assert result.status == POStatus.CANCELLED


@pytest.mark.asyncio
async def test_viewer_cannot_approve(db_session):
    requester = await _make_user(db_session, UserRole.REQUESTER)
    viewer = await _make_user(db_session, UserRole.VIEWER)
    po = await _make_po(db_session, requester.id, POStatus.PENDING_APPROVAL)
    svc = ApprovalService(db_session)
    with pytest.raises(AuthorizationException):
        await svc.approve(po.id, viewer)
