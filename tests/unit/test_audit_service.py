"""
Unit tests — app/services/audit_service.py
"""
import pytest
import uuid
from app.services.audit_service import AuditService
from app.domain.models.db_models import AuditLog


@pytest.mark.asyncio
async def test_audit_log_basic(db_session):
    svc = AuditService(db_session)
    entry = await svc.log(
        action="test.action",
        entity_type="TestEntity",
        entity_id="abc-123",
        new_values={"key": "value"},
    )
    assert isinstance(entry, AuditLog)
    assert entry.action == "test.action"
    assert entry.entity_type == "TestEntity"
    assert entry.entity_id == "abc-123"
    assert entry.new_values["key"] == "value"


@pytest.mark.asyncio
async def test_audit_log_login_success(db_session):
    svc = AuditService(db_session)
    user_id = uuid.uuid4()
    entry = await svc.log_login(user_id, "test@test.com", ip_address="127.0.0.1")
    assert entry.action == "auth.login"
    assert entry.user_id == user_id
    assert entry.new_values["success"] is True


@pytest.mark.asyncio
async def test_audit_log_po_transition(db_session):
    svc = AuditService(db_session)
    user_id = uuid.uuid4()
    entry = await svc.log_po_transition(
        user_id=user_id,
        po_id="po-1",
        from_status="draft",
        to_status="pending_approval",
    )
    assert entry.action == "po.pending_approval"
    assert entry.old_values["status"] == "draft"
    assert entry.new_values["status"] == "pending_approval"


@pytest.mark.asyncio
async def test_audit_log_vendor_change(db_session):
    svc = AuditService(db_session)
    entry = await svc.log_vendor_change(
        user_id=uuid.uuid4(),
        vendor_id="vnd-42",
        action="deactivate",
        changes={"status": "inactive"},
    )
    assert entry.action == "vendor.deactivate"
    assert entry.entity_id == "vnd-42"
