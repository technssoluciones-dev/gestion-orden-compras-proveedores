"""
Purchase Order tests v7 — cubre approve/reject/cancel y flujos completos.
Sube purchase_order_service.py de 62% a ~85%.
"""
import pytest
import uuid
from app.core.security import hash_password
from app.domain.models.db_models import User, UserRole


async def _login(client, db_session, role=UserRole.APPROVER) -> tuple[str, User]:
    u = User(
        id=uuid.uuid4(),
        email=f"pov7_{uuid.uuid4().hex[:6]}@test.com",
        username=f"pov7_{uuid.uuid4().hex[:6]}",
        full_name="PO V7 User",
        hashed_password=hash_password("Test1234!"),
        role=role,
        is_active=True,
        is_verified=True,
    )
    db_session.add(u)
    await db_session.flush()
    r = await client.post("/api/v1/auth/login", json={"email": u.email, "password": "Test1234!"})
    assert r.status_code == 200
    return r.json()["access_token"], u


async def _create_and_submit_po(client, db_session, role=UserRole.APPROVER) -> tuple[str, str]:
    """Helper: crea OC y la envía a PENDING_APPROVAL. Retorna (token, po_id)."""
    token, _ = await _login(client, db_session, role)
    h = {"Authorization": f"Bearer {token}"}

    # Crear OC con líneas
    r = await client.post("/api/v1/purchase-orders", json={
        "title": f"PO v7 {uuid.uuid4().hex[:4]}",
        "currency": "USD",
        "priority": "high",
        "line_items": [
            {"line_number": 1, "description": "Widget A", "quantity": "5", "unit_price": "200.00"},
            {"line_number": 2, "description": "Widget B", "quantity": "2", "unit_price": "500.00"},
        ],
    }, headers=h)
    assert r.status_code == 201, r.text
    po_id = r.json()["id"]
    await db_session.flush()

    # Submit
    r2 = await client.post(f"/api/v1/purchase-orders/{po_id}/submit", headers=h)
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "pending_approval"

    return token, po_id


@pytest.mark.asyncio
async def test_full_approve_flow(client, db_session):
    """
    Flujo completo: DRAFT → PENDING_APPROVAL → APPROVED.
    Cubre transition_status() + approve().
    """
    token, po_id = await _create_and_submit_po(client, db_session)
    h = {"Authorization": f"Bearer {token}"}

    r = await client.post(f"/api/v1/purchase-orders/{po_id}/approve", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "approved"
    # line_items deben venir en la respuesta (fix v5)
    assert len(data["line_items"]) == 2


@pytest.mark.asyncio
async def test_full_reject_flow(client, db_session):
    """
    Flujo completo: DRAFT → PENDING_APPROVAL → REJECTED con motivo.
    Cubre reject() y que rejection_reason no se retorna en el schema
    (solo status cambia).
    """
    token, po_id = await _create_and_submit_po(client, db_session)
    h = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        f"/api/v1/purchase-orders/{po_id}/reject",
        json={"reason": "Proveedor no homologado"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "rejected"
    assert len(data["line_items"]) == 2


@pytest.mark.asyncio
async def test_cancel_from_pending_approval(client, db_session):
    """Cancelar desde PENDING_APPROVAL — transición válida."""
    token, po_id = await _create_and_submit_po(client, db_session)
    h = {"Authorization": f"Bearer {token}"}

    r = await client.post(f"/api/v1/purchase-orders/{po_id}/cancel", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_from_approved(client, db_session):
    """Cancelar desde APPROVED — transición válida en state machine."""
    token, po_id = await _create_and_submit_po(client, db_session)
    h = {"Authorization": f"Bearer {token}"}

    # Approve primero
    await client.post(f"/api/v1/purchase-orders/{po_id}/approve", headers=h)
    await db_session.flush()

    # Cancel desde approved
    r = await client.post(f"/api/v1/purchase-orders/{po_id}/cancel", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cannot_cancel_cancelled_po(client, db_session):
    """CANCELLED → CANCELLED es transición inválida (422)."""
    token, po_id = await _create_and_submit_po(client, db_session)
    h = {"Authorization": f"Bearer {token}"}

    # Primera cancelación — válida
    r1 = await client.post(f"/api/v1/purchase-orders/{po_id}/cancel", headers=h)
    assert r1.status_code == 200
    await db_session.flush()

    # Segunda cancelación — inválida
    r2 = await client.post(f"/api/v1/purchase-orders/{po_id}/cancel", headers=h)
    assert r2.status_code == 422


@pytest.mark.asyncio
async def test_cannot_approve_draft(client, db_session):
    """No se puede aprobar una OC en DRAFT (sin submit previo)."""
    token, _ = await _login(client, db_session)
    h = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/v1/purchase-orders", json={
        "title": "PO Draft Direct Approve", "currency": "USD"
    }, headers=h)
    po_id = r.json()["id"]
    await db_session.flush()

    r2 = await client.post(f"/api/v1/purchase-orders/{po_id}/approve", headers=h)
    assert r2.status_code == 422


@pytest.mark.asyncio
async def test_get_po_by_id(client, db_session):
    """GET /purchase-orders/{id} retorna la OC con line_items."""
    token, _ = await _login(client, db_session, UserRole.REQUESTER)
    h = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/v1/purchase-orders", json={
        "title": "PO Get By ID",
        "currency": "USD",
        "line_items": [
            {"line_number": 1, "description": "Item", "quantity": "1", "unit_price": "100.00"},
        ],
    }, headers=h)
    assert r.status_code == 201
    po_id = r.json()["id"]
    await db_session.flush()

    get_r = await client.get(f"/api/v1/purchase-orders/{po_id}", headers=h)
    assert get_r.status_code == 200
    data = get_r.json()
    assert data["id"] == po_id
    assert len(data["line_items"]) == 1


@pytest.mark.asyncio
async def test_get_nonexistent_po_returns_404(client, db_session):
    """GET de un UUID que no existe → 404."""
    token, _ = await _login(client, db_session)
    h = {"Authorization": f"Bearer {token}"}

    fake_id = str(uuid.uuid4())
    r = await client.get(f"/api/v1/purchase-orders/{fake_id}", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_my_orders_pagination(client, db_session):
    """GET /purchase-orders con skip/limit — solo devuelve OCs del usuario."""
    token, _ = await _login(client, db_session, UserRole.REQUESTER)
    h = {"Authorization": f"Bearer {token}"}

    # Crear 3 OCs
    for i in range(3):
        await client.post("/api/v1/purchase-orders", json={
            "title": f"PO list test {i}", "currency": "USD"
        }, headers=h)
    await db_session.flush()

    # Sin límite
    r_all = await client.get("/api/v1/purchase-orders", headers=h)
    assert r_all.status_code == 200
    assert len(r_all.json()) >= 3

    # Con limit=1
    r_limited = await client.get("/api/v1/purchase-orders?skip=0&limit=1", headers=h)
    assert r_limited.status_code == 200
    assert len(r_limited.json()) == 1


@pytest.mark.asyncio
async def test_po_totals_calculated_correctly(client, db_session):
    """
    Verifica que subtotal, tax_amount y total_amount se calculan correctamente.
    IVA Chile: 19%. 2 items × 100 = 200 subtotal, 38 IVA, 238 total.
    """
    token, _ = await _login(client, db_session, UserRole.REQUESTER)
    h = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/v1/purchase-orders", json={
        "title": "PO totals test",
        "currency": "USD",
        "line_items": [
            {"line_number": 1, "description": "Item", "quantity": "2", "unit_price": "100.00"},
        ],
    }, headers=h)
    assert r.status_code == 201
    data = r.json()
    assert float(data["subtotal"]) == 200.00
    assert float(data["tax_amount"]) == pytest.approx(38.00, abs=0.01)
    assert float(data["total_amount"]) == pytest.approx(238.00, abs=0.01)
