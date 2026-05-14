"""Auth endpoint tests."""
import pytest
import uuid
from app.core.security import hash_password
from app.domain.models.db_models import User, UserRole


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    response = await client.post("/api/v1/auth/login", json={
        "email": "nonexistent@test.com",
        "password": "wrong"
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_success(client, db_session):
    user = User(
        id=uuid.uuid4(),
        email="login_test@procureflow.com",
        username="login_testuser",
        full_name="Test User",
        hashed_password=hash_password("Test1234!"),
        role=UserRole.REQUESTER,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()  # ← necesario: override_get_db no hace commit

    response = await client.post("/api/v1/auth/login", json={
        "email": "login_test@procureflow.com",
        "password": "Test1234!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_inactive_user(client, db_session):
    user = User(
        id=uuid.uuid4(),
        email="inactive@procureflow.com",
        username="inactive_user",
        full_name="Inactive User",
        hashed_password=hash_password("Test1234!"),
        role=UserRole.REQUESTER,
        is_active=False,  # ← desactivado
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    response = await client.post("/api/v1/auth/login", json={
        "email": "inactive@procureflow.com",
        "password": "Test1234!"
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_requires_auth(client):
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 403
