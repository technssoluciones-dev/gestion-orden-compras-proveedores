# ProcureFlow AI 🛒

# Plataforma Inteligente de Gestión de Órdenes de Compra y Proveedores

[![Python](https://img.shields.io/badge/Python-3.12-blue)][def]
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)](https://postgresql.org)

## Inicio Rápido

### Prerrequisitos
- Python 3.12+
- Docker & Docker Compose
- PostgreSQL 16 (o usar Docker)
- Redis 7 (o usar Docker)

### Instalación con Docker (recomendado)

```bash
# 1. Clonar y configurar
git clone <repo-url>
cd procureflow
cp .env.example .env
# Editar .env con tus valores reales

# 2. Levantar servicios
docker compose up -d

# 3. Seed de datos iniciales
docker compose exec api python scripts/seed.py
```

### Instalación local

```bash
# 1. Entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate    # Windows

# 2. Dependencias
pip install -r requirements.txt

# 3. Variables de entorno
cp .env.example .env
# Editar .env

# 4. Base de datos
alembic upgrade head

# 5. Seed inicial
python scripts/seed.py

# 6. Ejecutar
uvicorn app.main:app --reload --port 8000
```

## Credenciales por Defecto (solo desarrollo)

| Usuario | Email | Password | Rol |
|---------|-------|----------|-----|
| Admin | admin@procureflow.com | Admin1234! | ADMIN |
| Requester | requester@procureflow.com | Test1234! | REQUESTER |

## API Documentation

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Endpoints Principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | /api/v1/auth/login | Login |
| POST | /api/v1/auth/refresh | Renovar token |
| GET | /api/v1/users/me | Perfil actual |
| GET | /api/v1/vendors | Listar proveedores |
| POST | /api/v1/vendors | Crear proveedor (ADMIN/MANAGER) |
| GET | /api/v1/purchase-orders | Mis órdenes |
| POST | /api/v1/purchase-orders | Crear OC |
| POST | /api/v1/approvals/{id}/submit | Enviar a aprobación |
| POST | /api/v1/approvals/{id}/approve | Aprobar OC |
| POST | /api/v1/approvals/{id}/reject | Rechazar OC |
| GET | /api/v1/health | Liveness probe |
| GET | /api/v1/health/ready | Readiness probe |

## Ejecutar Tests

```bash
# Tests completos con cobertura
pytest tests/ --cov=app --cov-report=html

# Solo unitarios
pytest tests/unit/ -v

# Solo integración
pytest tests/integration/ -v

# Test específico
pytest tests/unit/test_security.py -v
```

## Arquitectura

```
app/
├── api/v1/routes/    # HTTP layer (FastAPI routers)
├── services/         # Business logic (Application layer)
├── repositories/     # Data access (Infrastructure layer)
├── domain/models/    # ORM models (Domain layer)
├── schemas/          # Pydantic DTOs
├── core/             # Config, security, DB, exceptions
├── middlewares/      # Rate limiting, logging, security headers
├── workers/          # Celery tasks
└── events/           # Event bus (domain events)
```

## Seguridad

- JWT HS256 con access + refresh tokens
- bcrypt para hash de passwords
- Rate limiting: 200 req/min global
- CORS configurado por entorno
- OWASP security headers
- RBAC por endpoint (ADMIN, MANAGER, APPROVER, FINANCE, REQUESTER, VIEWER)
- Auditoría completa de eventos de negocio

## Licencia

Propietario — Todos los derechos reservados.


[def]: https://python.org