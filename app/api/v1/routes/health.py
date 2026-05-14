"""
ProcureFlow AI — Health & Readiness endpoints
Incluye check de DB y Redis para monitoreo real.
"""
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("")
async def health_check():
    """Liveness probe — responde si la app está corriendo."""
    return {
        "status": "healthy",
        "app":     settings.app_name,
        "version": settings.app_version,
        "env":     settings.app_env,
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness probe — verifica DB y Redis.
    Devuelve 503 si algún componente crítico falla.
    """
    from fastapi import status as http_status
    from fastapi.responses import JSONResponse

    checks: dict = {}
    all_ok = True

    # ── Database check ────────────────────────────────────────────────────
    try:
        from app.core.database import check_db_connection
        db_ok = await check_db_connection()
        checks["database"] = "healthy" if db_ok else "unhealthy"
        if not db_ok:
            all_ok = False
    except Exception as e:
        checks["database"] = f"error: {str(e)[:100]}"
        all_ok = False

    # ── Redis check ───────────────────────────────────────────────────────
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unavailable: {str(e)[:80]}"
        # Redis no es crítico para arrancar — solo warning
        # all_ok = False  # descomentar si Redis es requerido

    response_data = {
        "status": "ready" if all_ok else "degraded",
        "app":    settings.app_name,
        "checks": checks,
    }

    status_code = http_status.HTTP_200_OK if all_ok else http_status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=response_data, status_code=status_code)
