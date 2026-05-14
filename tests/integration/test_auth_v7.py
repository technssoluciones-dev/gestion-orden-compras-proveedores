"""
Auth tests v7 — cubre refresh() y casos edge de login.
Sube auth_service.py de 54% a ~85%.
"""
import pytest
import uuid
from app.core.security import hash_password, create_refresh_token
from app.domain.models.db_models import User, UserRole


async def _create_active_user(db_session, role=UserRole.REQUESTER) -> User:
    u = User(
        id=uuid.uuid4(),
        email=f"authv7_{uuid.uuid4().hex[:6]}@test.com",
        username=f"authv7_{uuid.uuid4().hex[:6]}",
        full_name="Auth V7 User",
        hashed_password=hash_password("Test1234!"),
        role=role,
        is_active=True,
        is_verified=True,
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.mark.asyncio
async def test_login_returns_both_tokens(client, db_session):
    """Login exitoso devuelve access_token, refresh_token y token_type."""
    user = await _create_active_user(db_session)
    r = await client.post("/api/v1/auth/login", json={
        "email": user.email, "password": "Test1234!"
    })
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    # Los tokens deben ser strings no vacíos
    assert len(data["access_token"]) > 10
    assert len(data["refresh_token"]) > 10


@pytest.mark.asyncio
async def test_login_wrong_password(client, db_session):
    """Password incorrecto → 401."""
    user = await _create_active_user(db_session)
    r = await client.post("/api/v1/auth/login", json={
        "email": user.email, "password": "WrongPassword!"
    })
    assert r.status_code == 401
    assert "error" in r.json()


@pytest.mark.asyncio
async def test_login_nonexistent_email(client):
    """Email que no existe → 401 (mismo mensaje que password incorrecto, timing-safe)."""
    r = await client.post("/api/v1/auth/login", json={
        "email": "nobody@nowhere.com", "password": "Test1234!"
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_user_rejected(client, db_session):
    """Usuario inactivo → 401 aunque password sea correcto."""
    u = User(
        id=uuid.uuid4(),
        email=f"inactive_v7_{uuid.uuid4().hex[:6]}@test.com",
        username=f"inactive_v7_{uuid.uuid4().hex[:6]}",
        full_name="Inactive",
        hashed_password=hash_password("Test1234!"),
        role=UserRole.REQUESTER,
        is_active=False,
        is_verified=True,
    )
    db_session.add(u)
    await db_session.flush()

    r = await client.post("/api/v1/auth/login", json={
        "email": u.email, "password": "Test1234!"
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_cycle(client, db_session):
    """
    Ciclo completo: login → usar refresh_token → obtener nuevo access_token.
    Cubre auth_service.refresh() (principal gap de cobertura).
    """
    user = await _create_active_user(db_session)
    # Step 1: login
    login_r = await client.post("/api/v1/auth/login", json={
        "email": user.email, "password": "Test1234!"
    })
    assert login_r.status_code == 200
    refresh_token = login_r.json()["refresh_token"]

    # Step 2: refresh
    refresh_r = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert refresh_r.status_code == 200, f"refresh falló: {refresh_r.text}"
    data = refresh_r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # El nuevo access token debe ser diferente al login inicial
    # (timestamps diferentes → JWTs diferentes)
    assert data["access_token"] != login_r.json()["access_token"]


@pytest.mark.asyncio
async def test_refresh_with_invalid_token(client):
    """Token malformado → 401."""
    r = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": "not.a.valid.jwt.token"
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_access_token_rejected(client, db_session):
    """
    Usar access_token donde se espera refresh_token → 401.
    Valida que verify_token_type() rechaza el tipo incorrecto.
    """
    user = await _create_active_user(db_session)
    login_r = await client.post("/api/v1/auth/login", json={
        "email": user.email, "password": "Test1234!"
    })
    access_token = login_r.json()["access_token"]

    r = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": access_token  # tipo incorrecto
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_valid_token(client, db_session):
    """GET /users/me con token válido → 200 con perfil del usuario."""
    user = await _create_active_user(db_session, role=UserRole.ADMIN)
    login_r = await client.post("/api/v1/auth/login", json={
        "email": user.email, "password": "Test1234!"
    })
    token = login_r.json()["access_token"]

    me_r = await client.get("/api/v1/users/me", headers={
        "Authorization": f"Bearer {token}"
    })
    assert me_r.status_code == 200
    data = me_r.json()
    assert data["email"] == user.email
    assert data["role"] == user.role.value


@pytest.mark.asyncio
async def test_get_me_without_token_returns_403(client):
    """Sin token → 403 (HTTPBearer levanta 403, no 401)."""
    r = await client.get("/api/v1/users/me")
    assert r.status_code == 403
