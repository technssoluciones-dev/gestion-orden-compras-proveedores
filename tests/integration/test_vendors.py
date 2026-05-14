"""Integration tests — Vendors CRUD.

NOTA: el fixture client usa override_get_db que NO hace commit automático.
Usamos db_session.flush() para hacer visible el usuario antes del login.
"""
import pytest
import uuid
from app.core.security import hash_password
from app.domain.models.db_models import User, UserRole


async def _make_admin_and_login(client, db_session) -> str:
    """Crea usuario ADMIN, hace flush y retorna access token."""
    user = User(
        id=uuid.uuid4(),
        email=f"admin_{uuid.uuid4().hex[:6]}@test.com",
        username=f"admin_{uuid.uuid4().hex[:6]}",
        full_name="Test Admin",
        hashed_password=hash_password("Test1234!"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()  # hace visible el usuario en la misma sesión

    response = await client.post("/api/v1/auth/login", json={
        "email": user.email,
        "password": "Test1234!",
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_create_vendor(client, db_session):
    token = await _make_admin_and_login(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    code = f"ACME-{uuid.uuid4().hex[:6].upper()}"
    payload = {
        "name": "Acme Corp",
        "vendor_code": code,
        "email": "acme@example.com",
        "payment_terms": 30,
        "currency": "USD",
    }
    response = await client.post("/api/v1/vendors", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["vendor_code"] == code
    assert data["name"] == "Acme Corp"
    assert data["status"] == "pending_review"


@pytest.mark.asyncio
async def test_create_vendor_duplicate_code(client, db_session):
    token = await _make_admin_and_login(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    code = f"DUP-{uuid.uuid4().hex[:6].upper()}"
    payload = {"name": "Dup Vendor", "vendor_code": code}
    r1 = await client.post("/api/v1/vendors", json=payload, headers=headers)
    assert r1.status_code == 201
    await db_session.flush()  # aseguramos visibilidad para el segundo intento

    r2 = await client.post("/api/v1/vendors", json=payload, headers=headers)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_list_vendors_requires_auth(client):
    response = await client.get("/api/v1/vendors")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_vendors_admin_sees_all(client, db_session):
    """Admin debe ver vendors en todos los estados (no solo ACTIVE)."""
    token = await _make_admin_and_login(client, db_session)
    headers = {"Authorization": f"Bearer {token}"}

    # Crear vendor (estado PENDING_REVIEW por defecto)
    code = f"VND-{uuid.uuid4().hex[:6].upper()}"
    r = await client.post("/api/v1/vendors", json={
        "name": "Pending Vendor", "vendor_code": code
    }, headers=headers)
    assert r.status_code == 201
    await db_session.flush()

    list_r = await client.get("/api/v1/vendors", headers=headers)
    assert list_r.status_code == 200
    codes_in_list = [v["vendor_code"] for v in list_r.json()]
    assert code in codes_in_list, (
        f"Admin no puede ver vendor recién creado (PENDING_REVIEW). "
        f"Codes encontrados: {codes_in_list}"
    )
