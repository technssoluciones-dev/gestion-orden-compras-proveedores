"""
ProcureFlow AI — FastAPI Application Entry Point
v7: integra rate limiting y mejora de headers de seguridad.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.core.config import settings
from app.core.database import create_db_tables
from app.core.exceptions import ProcureFlowException
from app.api.v1.router import api_router
from app.middlewares.logging_middleware import RequestLoggingMiddleware
from app.middlewares.security_headers import SecurityHeadersMiddleware
from app.middlewares.rate_limiting import setup_rate_limiter
from app.core.structured_logging import setup_logging

setup_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("procureflow_starting", version=settings.app_version, env=settings.app_env)
    await create_db_tables()
    logger.info("procureflow_ready")
    yield
    logger.info("procureflow_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Intelligent Purchase Order & Vendor Management Platform",
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Rate limiting (slowapi) — ANTES de otros middlewares ──────────────
    setup_rate_limiter(app)

    # ── Middleware stack ───────────────────────────────────────────────────
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts.split(","),
    )

    # ── Exception Handlers ─────────────────────────────────────────────────

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.info("validation_error", path=str(request.url), errors=exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors(),
            },
        )

    @app.exception_handler(ProcureFlowException)
    async def procureflow_exception_handler(request: Request, exc: ProcureFlowException):
        logger.warning("domain_exception", code=exc.code, message=exc.message, path=str(request.url))
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error("unhandled_exception", error=str(exc), path=str(request.url))
        return JSONResponse(
            status_code=500,
            content={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
        )

    # ── Routers ────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
