"""
Integration tests — Purchase Orders completos v7.
Cubre approve, reject (con reason), cancel y cálculo de totales con IVA.
"""
import pytest
import uuid
from app.core.security import hash_password
from app.domain.models.db_models import User, UserRole


async def _login(client, db_session, role=UserRole.APPROVER):
    u = User(
        id=uuid.uuid4(),
        email=f"poc_{uuid.uuid4().hex[:6]}@test.com",
        username=f"poc_{uuid.uuid4().hex[:6]}",
        full_name="PO Complete Test",
        hashed_password=hash_password("Test1234!"),
        role=role,
        is_active=True,
        is_verified=True,
    )
    db_session.add(u)
    await db_session.flush()
    r = await client.post("/api/v1/auth/login", json={"email": u.email, "password": "Test1234!"})
    assert r.status_code == 200
    return r.json()["access_token"]


async def _create_and_submit(client, db_session, token):
    """Helper: crea una OC con items y la envía a aprobación."""
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/v1/purchase-orders", json={
        "title": "Full Flow PO",
        "currency": "USD",
        "line_items": [
            {"line_number": 1, "description": "Server", "quantity": "1", "unit_price": "1000.00"},
        ],
    }, headers=h)
    assert r.status_code == 201
    po_id = r.json()["id"]
    await db_session.flush()

    r2 = await client.post(f"/api/v1/purchase-orders/{po_id}/submit", headers=h)
    assert r2.status_code == 200
    assert r2.json()["status"] == "pending_approval"
    await db_session.flush()
    return po_id, h


@pytest.mark.asyncio
async def test_po_full_approval_flow(client, db_session):
    """DRAFT → PENDING_APPROVAL → APPROVED"""
    token = await _login(client, db_session, UserRole.APPROVER)
    po_id, h = await _create_and_submit(client, db_session, token)

    r = await client.post(f"/api/v1/purchase-orders/{po_id}/approve", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "approved"
    assert len(data["line_items"]) == 1  # eager-loaded


@pytest.mark.asyncio
async def test_po_reject_flow(client, db_session):
    """DRAFT → PENDING_APPROVAL → REJECTED (con reason)"""
    token = await _login(client, db_session, UserRole.APPROVER)
    po_id, h = await _create_and_submit(client, db_session, token)

    r = await client.post(f"/api/v1/purchase-orders/{po_id}/reject",
                          json={"reason": "No hay presupuesto disponible"},
                          headers=h)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "rejected"


@pytest.mark.asyncio
async def test_po_cancel_from_pending(client, db_session):
    """DRAFT → PENDING_APPROVAL → CANCELLED"""
    token = await _login(client, db_session, UserRole.APPROVER)
    po_id, h = await _create_and_submit(client, db_session, token)

    r = await client.post(f"/api/v1/purchase-orders/{po_id}/cancel", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_po_totals_with_iva(client, db_session):
    """Subtotal, tax (19%) y total_amount calculados correctamente."""
    token = await _login(client, db_session, UserRole.REQUESTER)
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/v1/purchase-orders", json={
        "title": "IVA Test",
        "currency": "CLP",
        "line_items": [
            {"line_number": 1, "description": "Item 1", "quantity": "2", "unit_price": "100.00"},
            {"line_number": 2, "description": "Item 2", "quantity": "1", "unit_price": "200.00"},
        ],
    }, headers=h)
    assert r.status_code == 201
    data = r.json()
    # subtotal = 2*100 + 1*200 = 400
    assert float(data["subtotal"]) == pytest.approx(400.00)
    # tax = 400 * 0.19 = 76
    assert float(data["tax_amount"]) == pytest.approx(76.00)
    # total = 400 + 76 = 476
    assert float(data["total_amount"]) == pytest.approx(476.00)


@pytest.mark.asyncio
async def test_po_list_pagination(client, db_session):
    """GET /purchase-orders con skip/limit."""
    token = await _login(client, db_session, UserRole.REQUESTER)
    h = {"Authorization": f"Bearer {token}"}

    # Crear 3 OCs
    for i in range(3):
        await client.post("/api/v1/purchase-orders", json={
            "title": f"Pag PO {i}", "currency": "USD"
        }, headers=h)
    await db_session.flush()

    r = await client.get("/api/v1/purchase-orders?skip=0&limit=2", headers=h)
    assert r.status_code == 200
    assert len(r.json()) <= 2


@pytest.mark.asyncio
async def test_po_not_found(client, db_session):
    """GET /purchase-orders/{id} con UUID inexistente devuelve 404."""
    token = await _login(client, db_session, UserRole.REQUESTER)
    h = {"Authorization": f"Bearer {token}"}
    r = await client.get(f"/api/v1/purchase-orders/{uuid.uuid4()}", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_po_invalid_approve_from_draft(client, db_session):
    """No se puede aprobar directamente desde DRAFT (máquina de estados)."""
    token = await _login(client, db_session, UserRole.APPROVER)
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/v1/purchase-orders", json={
        "title": "Invalid approve", "currency": "USD"
    }, headers=h)
    po_id = r.json()["id"]
    await db_session.flush()
    r2 = await client.post(f"/api/v1/purchase-orders/{po_id}/approve", headers=h)
    assert r2.status_code == 422
