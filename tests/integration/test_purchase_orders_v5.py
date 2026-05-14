"""
Tests adicionales v5 — Purchase Order state transitions con line_items.

Valida que los endpoints submit/approve/reject/cancel devuelvan
line_items correctamente (fix del bug MissingGreenlet en PO repo).
"""
import pytest
import uuid
from app.core.security import hash_password
from app.domain.models.db_models import User, UserRole


async def _login(client, db_session, role=UserRole.APPROVER):
    u = User(
        id=uuid.uuid4(),
        email=f"v5_{uuid.uuid4().hex[:6]}@test.com",
        username=f"v5_{uuid.uuid4().hex[:6]}",
        full_name="V5 Test",
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


@pytest.mark.asyncio
async def test_submit_returns_line_items(client, db_session):
    """
    Valida fix v5: PurchaseOrderRepository.update() ahora usa
    get_by_id_with_items(). Sin el fix, submit devolvía line_items=[]
    o lanzaba MissingGreenlet.
    """
    token = await _login(client, db_session, UserRole.REQUESTER)
    h = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/v1/purchase-orders", json={
        "title": "PO con items v5",
        "currency": "USD",
        "line_items": [
            {"line_number": 1, "description": "Item A", "quantity": "3", "unit_price": "100.00"},
        ],
    }, headers=h)
    assert r.status_code == 201, r.text
    po_id = r.json()["id"]
    assert len(r.json()["line_items"]) == 1  # creado con items
    await db_session.flush()

    r2 = await client.post(f"/api/v1/purchase-orders/{po_id}/submit", headers=h)
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert data["status"] == "pending_approval"
    # Bug v5: sin el fix, line_items era [] aquí
    assert len(data["line_items"]) == 1, (
        "line_items vacío tras submit — PO repo.update() no usa selectinload"
    )


@pytest.mark.asyncio
async def test_cancel_returns_line_items(client, db_session):
    """Valida que /cancel también devuelva line_items (mismo fix)."""
    token = await _login(client, db_session, UserRole.REQUESTER)
    h = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/v1/purchase-orders", json={
        "title": "PO cancel v5",
        "currency": "USD",
        "line_items": [
            {"line_number": 1, "description": "Widget", "quantity": "1", "unit_price": "50.00"},
        ],
    }, headers=h)
    assert r.status_code == 201
    po_id = r.json()["id"]
    await db_session.flush()

    r2 = await client.post(f"/api/v1/purchase-orders/{po_id}/cancel", headers=h)
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "cancelled"
    assert len(r2.json()["line_items"]) == 1


@pytest.mark.asyncio
async def test_refresh_token_works(client, db_session):
    """
    Valida fix v5: auth_service.refresh() ahora convierte sub a UUID.
    Sin el fix, refresh lanzaba error de PostgreSQL en producción.
    """
    user = User(
        id=uuid.uuid4(),
        email=f"refresh_{uuid.uuid4().hex[:6]}@test.com",
        username=f"refresh_{uuid.uuid4().hex[:6]}",
        full_name="Refresh Test",
        hashed_password=hash_password("Test1234!"),
        role=UserRole.REQUESTER,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    login_r = await client.post("/api/v1/auth/login", json={
        "email": user.email, "password": "Test1234!"
    })
    assert login_r.status_code == 200
    refresh_token = login_r.json()["refresh_token"]

    refresh_r = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert refresh_r.status_code == 200, (
        f"refresh() falló — probable UUID str bug: {refresh_r.text}"
    )
    assert "access_token" in refresh_r.json()
