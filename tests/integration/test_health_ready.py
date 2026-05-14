"""
Integration tests — Health endpoints.
Cubre /health y /health/ready.
"""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_health_liveness(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "app" in data
    assert "env" in data


@pytest.mark.asyncio
async def test_health_ready_db_ok(client):
    """
    /ready con DB funcional devuelve 200 (o 503 si Redis no está).
    En tests usamos SQLite, así que DB = OK.
    """
    with patch("app.api.v1.routes.health.check_db_connection", new_callable=AsyncMock, return_value=True):
        r = await client.get("/api/v1/health/ready")
    # Puede ser 200 (todo OK) o 503 (Redis no disponible en CI)
    assert r.status_code in (200, 503)
    data = r.json()
    assert data["checks"]["database"] == "healthy"


@pytest.mark.asyncio
async def test_health_ready_db_fail(client):
    """Cuando la DB falla, /ready devuelve 503."""
    with patch("app.api.v1.routes.health.check_db_connection", new_callable=AsyncMock, return_value=False):
        r = await client.get("/api/v1/health/ready")
    assert r.status_code == 503
    data = r.json()
    assert data["status"] == "degraded"
    assert data["checks"]["database"] == "unhealthy"
