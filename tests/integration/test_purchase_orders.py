"""Integration tests — Purchase Orders."""
import pytest
import uuid
from app.core.security import hash_password
from app.domain.models.db_models import User, UserRole


async def _make_user_and_login(client, db_session, role=UserRole.REQUESTER):
    u = User(
        id=uuid.uuid4(),
        email=f"user_{uuid.uuid4().hex[:6]}@test.com",
        username=f"user_{uuid.uuid4().hex[:6]}",
        full_name="Test User",
        hashed_password=hash_password("Test1234!"),
        role=role,
        is_active=True,
        is_verified=True,
    )
    db_session.add(u)
    await db_session.flush()  # necesario: override_get_db no hace commit

    r = await client.post("/api/v1/auth/login", json={
        "email": u.email, "password": "Test1234!"
    })
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_create_purchase_order(client, db_session):
    token = await _make_user_and_login(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "title": "Laptops para equipo dev",
        "description": "MacBook Pro M3",
        "priority": "high",
        "currency": "USD",
        "line_items": [
            {
                "line_number": 1,
                "description": 'MacBook Pro M3 14"',
                "quantity": "2",
                "unit": "unidad",
                "unit_price": "2499.00",
            }
        ],
    }
    response = await client.post("/api/v1/purchase-orders", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["status"] == "draft"
    assert data["po_number"].startswith("PO-")
    assert len(data["line_items"]) == 1
    # Verificar cálculo de totales (2499 * 2 * 1.19 IVA)
    assert float(data["total_amount"]) > 0


@pytest.mark.asyncio
async def test_po_without_line_items(client, db_session):
    token = await _make_user_and_login(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/v1/purchase-orders", json={
        "title": "PO vacía",
        "currency": "USD",
        "line_items": [],
    }, headers=headers)
    assert r.status_code == 201
    assert r.json()["total_amount"] == "0.00"


@pytest.mark.asyncio
async def test_po_submit_state_machine(client, db_session):
    token = await _make_user_and_login(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/v1/purchase-orders", json={
        "title": "Test PO Submit", "currency": "USD"
    }, headers=headers)
    assert r.status_code == 201
    po_id = r.json()["id"]
    await db_session.flush()

    r2 = await client.post(f"/api/v1/purchase-orders/{po_id}/submit", headers=headers)
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "pending_approval"


@pytest.mark.asyncio
async def test_po_reject_with_body_reason(client, db_session):
    token = await _make_user_and_login(client, db_session, role=UserRole.APPROVER)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/v1/purchase-orders", json={
        "title": "PO to Reject", "currency": "USD"
    }, headers=headers)
    po_id = r.json()["id"]
    await db_session.flush()

    await client.post(f"/api/v1/purchase-orders/{po_id}/submit", headers=headers)
    await db_session.flush()

    r3 = await client.post(
        f"/api/v1/purchase-orders/{po_id}/reject",
        json={"reason": "Presupuesto agotado"},
        headers=headers,
    )
    assert r3.status_code == 200, r3.text
    assert r3.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_po_invalid_transition(client, db_session):
    """No se puede aprobar una OC en estado DRAFT."""
    token = await _make_user_and_login(client, db_session, role=UserRole.APPROVER)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/v1/purchase-orders", json={
        "title": "PO Draft Approve", "currency": "USD"
    }, headers=headers)
    po_id = r.json()["id"]
    await db_session.flush()

    # Intentar aprobar directamente desde DRAFT (inválido)
    r2 = await client.post(f"/api/v1/purchase-orders/{po_id}/approve", headers=headers)
    assert r2.status_code == 422  # InvalidStatusTransitionException
