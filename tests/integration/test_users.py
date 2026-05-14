"""
User management tests — app/api/v1/routes/users.py (53% → ~80%).
Cubre POST /users (requiere ADMIN), GET /users/{id}, GET /users/me.
"""
import pytest
import uuid
from app.core.security import hash_password
from app.domain.models.db_models import User, UserRole


async def _login_as(client, db_session, role: UserRole) -> str:
    u = User(
        id=uuid.uuid4(),
        email=f"usr_{role.value}_{uuid.uuid4().hex[:6]}@test.com",
        username=f"usr_{role.value}_{uuid.uuid4().hex[:6]}",
        full_name=f"User {role.value}",
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
async def test_create_user_as_admin(client, db_session):
    """ADMIN puede crear nuevos usuarios vía POST /users."""
    token = await _login_as(client, db_session, UserRole.ADMIN)
    h = {"Authorization": f"Bearer {token}"}

    new_email = f"newuser_{uuid.uuid4().hex[:6]}@test.com"
    r = await client.post("/api/v1/users", json={
        "email": new_email,
        "username": f"newuser_{uuid.uuid4().hex[:6]}",
        "full_name": "New User",
        "password": "NewPass123!",
        "role": "requester",
    }, headers=h)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["email"] == new_email
    assert data["role"] == "requester"
    assert "hashed_password" not in data  # nunca exponer el hash


@pytest.mark.asyncio
async def test_create_user_as_manager_forbidden(client, db_session):
    """MANAGER no puede crear usuarios — solo ADMIN."""
    token = await _login_as(client, db_session, UserRole.MANAGER)
    h = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/v1/users", json={
        "email": f"blocked_{uuid.uuid4().hex[:6]}@test.com",
        "username": f"blocked_{uuid.uuid4().hex[:6]}",
        "full_name": "Blocked",
        "password": "Test1234!",
    }, headers=h)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_create_user_duplicate_email(client, db_session):
    """Crear usuario con email duplicado → 409."""
    token = await _login_as(client, db_session, UserRole.ADMIN)
    h = {"Authorization": f"Bearer {token}"}

    email = f"dup_{uuid.uuid4().hex[:6]}@test.com"
    payload = {
        "email": email,
        "username": f"dup_{uuid.uuid4().hex[:6]}",
        "full_name": "Dup User",
        "password": "Test1234!",
    }
    r1 = await client.post("/api/v1/users", json=payload, headers=h)
    assert r1.status_code == 201
    await db_session.flush()

    # Segundo intento con mismo email (username diferente)
    payload["username"] = f"dup2_{uuid.uuid4().hex[:6]}"
    r2 = await client.post("/api/v1/users", json=payload, headers=h)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_get_user_by_id(client, db_session):
    """GET /users/{id} retorna el perfil del usuario."""
    # Crear un usuario target
    target = User(
        id=uuid.uuid4(),
        email=f"target_{uuid.uuid4().hex[:6]}@test.com",
        username=f"target_{uuid.uuid4().hex[:6]}",
        full_name="Target User",
        hashed_password=hash_password("Test1234!"),
        role=UserRole.REQUESTER,
        is_active=True,
        is_verified=True,
    )
    db_session.add(target)
    await db_session.flush()

    token = await _login_as(client, db_session, UserRole.ADMIN)
    h = {"Authorization": f"Bearer {token}"}

    r = await client.get(f"/api/v1/users/{target.id}", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == str(target.id)
    assert data["email"] == target.email


@pytest.mark.asyncio
async def test_get_nonexistent_user_returns_404(client, db_session):
    """GET /users/{uuid_no_existente} → 404."""
    token = await _login_as(client, db_session, UserRole.ADMIN)
    h = {"Authorization": f"Bearer {token}"}

    fake_id = str(uuid.uuid4())
    r = await client.get(f"/api/v1/users/{fake_id}", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_me_returns_current_user(client, db_session):
    """GET /users/me retorna el usuario autenticado."""
    user = User(
        id=uuid.uuid4(),
        email=f"mev7_{uuid.uuid4().hex[:6]}@test.com",
        username=f"mev7_{uuid.uuid4().hex[:6]}",
        full_name="Me V7",
        hashed_password=hash_password("Test1234!"),
        role=UserRole.FINANCE,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    r = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "Test1234!"})
    token = r.json()["access_token"]

    me_r = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me_r.status_code == 200
    data = me_r.json()
    assert data["email"] == user.email
    assert data["role"] == "finance"
    assert data["is_active"] is True
