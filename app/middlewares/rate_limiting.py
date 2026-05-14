"""
Rate limiting middleware — slowapi (Starlette-native limiter).

Configura dos niveles:
  - 200 req/minuto por IP   (global)
  - 10  req/minuto por IP   (solo endpoints /auth/*)

Uso en main.py:
    from app.middlewares.rate_limiting import setup_rate_limiter
    setup_rate_limiter(app)
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False

import structlog

logger = structlog.get_logger(__name__)

# Singleton limiter (import this in routes that need per-route limits)
limiter = None


def setup_rate_limiter(app: FastAPI) -> None:
    """
    Monta SlowAPI sobre la app FastAPI.

    Si slowapi no está instalado, registra un warning y continúa
    (no falla el arranque — degradación controlada).
    """
    global limiter
    if not SLOWAPI_AVAILABLE:
        logger.warning(
            "slowapi_not_installed",
            msg="Rate limiting desactivado. Instalar: pip install slowapi",
        )
        return

    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200/minute"],
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    logger.info("rate_limiter_configured", default_limit="200/minute")
