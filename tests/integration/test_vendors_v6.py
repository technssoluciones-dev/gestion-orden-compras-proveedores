"""
Integration tests — Vendors v6.
Valida guards de rol, paginación y endpoint deactivate.
"""
import pytest
import uuid
from app.core.security import hash_password
from app.domain.models.db_models import User, UserRole


async def _make_user_login(client, db_session, role: UserRole) -> str:
    u = User(
        id=uuid.uuid4(),
        email=f"{role.value}_{uuid.uuid4().hex[:6]}@test.com",
        username=f"{role.value}_{uuid.uuid4().hex[:6]}",
        full_name=f"Test {role.value.title()}",
        hashed_password=hash_password("Test1234!"),
        role=role,
        is_active=True,
        is_verified=True,
    )
    db_session.add(u)
    await db_session.flush()
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": u.email, "password": "Test1234!"},
    )
    assert r.status_code == 200, f"Login failed for {role}: {r.text}"
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_viewer_cannot_create_vendor(client, db_session):
    """
    Fix v6: POST /vendors ahora requiere ADMIN o MANAGER.
    Un VIEWER (o REQUESTER) no debería poder crear vendors.
    """
    token = await _make_user_login(client, db_session, UserRole.VIEWER)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/v1/vendors", json={
        "name": "Evil Corp",
        "vendor_code": f"EVIL-{uuid.uuid4().hex[:4].upper()}",
    }, headers=headers)
    assert r.status_code == 403, (
        f"VIEWER no debería poder crear vendors. Got {r.status_code}: {r.text}"
    )


@pytest.mark.asyncio
async def test_requester_cannot_create_vendor(client, db_session):
    """REQUESTER tampoco puede crear vendors."""
    token = await _make_user_login(client, db_session, UserRole.REQUESTER)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/v1/vendors", json={
        "name": "Corp X",
        "vendor_code": f"CORPX-{uuid.uuid4().hex[:4].upper()}",
    }, headers=headers)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_manager_can_create_vendor(client, db_session):
    """MANAGER puede crear vendors."""
    token = await _make_user_login(client, db_session, UserRole.MANAGER)
    headers = {"Authorization": f"Bearer {token}"}

    code = f"MGR-{uuid.uuid4().hex[:6].upper()}"
    r = await client.post("/api/v1/vendors", json={
        "name": "Manager Vendor",
        "vendor_code": code,
    }, headers=headers)
    assert r.status_code == 201, r.text
    assert r.json()["vendor_code"] == code


@pytest.mark.asyncio
async def test_activate_deactivate_cycle(client, db_session):
    """
    Fix v6: endpoint /deactivate ahora existe.
    Valida el ciclo completo activate → deactivate.
    """
    token = await _make_user_login(client, db_session, UserRole.ADMIN)
    h = {"Authorization": f"Bearer {token}"}

    code = f"CYCLE-{uuid.uuid4().hex[:6].upper()}"
    create_r = await client.post("/api/v1/vendors", json={
        "name": "Cycle Vendor",
        "vendor_code": code,
    }, headers=h)
    assert create_r.status_code == 201
    vid = create_r.json()["id"]
    await db_session.flush()

    # Activate
    act_r = await client.post(f"/api/v1/vendors/{vid}/activate", headers=h)
    assert act_r.status_code == 200, act_r.text
    assert act_r.json()["status"] == "active"

    # Deactivate (nuevo endpoint v6)
    deact_r = await client.post(f"/api/v1/vendors/{vid}/deactivate", headers=h)
    assert deact_r.status_code == 200, (
        f"Endpoint /deactivate no encontrado o falló: {deact_r.text}"
    )
    assert deact_r.json()["status"] == "inactive"


@pytest.mark.asyncio
async def test_list_vendors_pagination(client, db_session):
    """
    Fix v6: GET /vendors ahora acepta skip/limit.
    Valida que la paginación funciona correctamente.
    """
    token = await _make_user_login(client, db_session, UserRole.ADMIN)
    h = {"Authorization": f"Bearer {token}"}

    # Crear 3 vendors
    codes = []
    for i in range(3):
        code = f"PAG-{uuid.uuid4().hex[:6].upper()}"
        codes.append(code)
        r = await client.post("/api/v1/vendors", json={
            "name": f"Pagination Vendor {i}",
            "vendor_code": code,
        }, headers=h)
        assert r.status_code == 201
    await db_session.flush()

    # Pedir solo 1 registro
    r1 = await client.get("/api/v1/vendors?skip=0&limit=1", headers=h)
    assert r1.status_code == 200
    assert len(r1.json()) == 1

    # Pedir desde skip=1
    r2 = await client.get("/api/v1/vendors?skip=1&limit=10", headers=h)
    assert r2.status_code == 200
    # Al menos 1 registro más (los otros vendors del DB de test)
    assert len(r2.json()) >= 1
