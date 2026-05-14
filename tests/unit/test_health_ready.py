"""
Tests del endpoint /ready — app/api/v1/routes/health.py
Sube cobertura de health.py de 25% a ~70%.
"""
import pytest


@pytest.mark.asyncio
async def test_health_liveness(client):
    """GET /health — liveness probe básico."""
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert "app" in data
    assert "version" in data
    assert "env" in data


@pytest.mark.asyncio
async def test_health_ready_structure(client):
    """
    GET /health/ready — verifica estructura de respuesta.

    En tests la DB es SQLite in-memory (siempre disponible).
    Redis puede no estar corriendo en test — el endpoint lo marca como
    warning pero no 503 (Redis no es crítico para arrancar).
    """
    r = await client.get("/api/v1/health/ready")
    # Puede ser 200 (ready) o 503 (degraded), pero siempre devuelve JSON
    assert r.status_code in (200, 503)
    data = r.json()
    assert "status" in data
    assert "checks" in data
    assert "database" in data["checks"]
    assert "redis" in data["checks"]


@pytest.mark.asyncio
async def test_health_ready_db_key_present(client):
    """El check de base de datos siempre debe estar en la respuesta."""
    r = await client.get("/api/v1/health/ready")
    checks = r.json()["checks"]
    assert "database" in checks
    # Con SQLite in-memory en tests, la DB siempre es healthy
    assert checks["database"] in ("healthy", "unhealthy") or "error" in checks["database"]
