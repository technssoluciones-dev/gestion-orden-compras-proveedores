# ProcureFlow AI — Troubleshooting Guide

## Problemas más comunes

### App no arranca — ImportError en startup

```
ImportError: cannot import name 'create_access_token' from 'app.core.security'
```

**Causa:** `app/core/security.py` sólo tenía `hash_password`/`verify_password`.  
**Fix:** Ejecutar `python actualizacion_proyecto_v6.py` — ya incluye las funciones JWT.

---

### Tests fallan con `DeprecationWarning: event_loop`

```
DeprecationWarning: Replacing the event_loop fixture with a custom implementation
is deprecated and will lead to errors in the future.
```

**Causa:** `tests/conftest.py` define un fixture `event_loop` custom (patrón antiguo).  
**Fix:** Ejecutar `python actualizacion_proyecto_v7.py` — elimina el fixture y agrega
`asyncio_default_fixture_loop_scope = session` en `pytest.ini`.

---

### Vendor 403 en POST /vendors con usuario normal

**Causa:** El endpoint requiere rol `ADMIN` o `MANAGER`.  
**Fix (v6):** Ya aplicado. Asegúrate de hacer login con un usuario con rol adecuado.

---

### `MissingGreenlet` en endpoints submit/approve/cancel

**Causa:** SQLAlchemy intenta cargar `line_items` en contexto async sin eager load.  
**Fix (v5):** `PurchaseOrderRepository.update()` usa `get_by_id_with_items()` con
`selectinload`. Ya aplicado.

---

### DB no conecta en Docker

```bash
# Verificar que el contenedor postgres esté sano:
docker-compose ps
# Revisar logs:
docker-compose logs db
# Healthcheck manual:
docker exec procureflow-db pg_isready -U procureflow
```

---

### Celery worker no procesa tareas

```bash
# Ver si el broker está corriendo:
docker-compose ps rabbitmq
# Arrancar worker manualmente:
celery -A app.workers.celery_app worker --loglevel=info
# Verificar tareas en cola:
celery -A app.workers.celery_app inspect active
```

---

### Alembic no detecta cambios en modelos

```bash
# Asegurarse de que todos los modelos están importados en env.py
# Generar migración autogenerada:
alembic revision --autogenerate -m "descripcion_del_cambio"
# Aplicar:
alembic upgrade head
# Rollback último:
alembic downgrade -1
```

---

### Coverage < 100%

```bash
# Ver reporte detallado:
pytest --cov=app --cov-report=html tests/
open htmlcov/index.html

# Módulos con 0% (workers, ai): requieren broker/API key real para testar.
# Usar pytest-mock para mockear las dependencias externas.
```

---

## Comandos de desarrollo

```bash
# Stack completo
docker-compose up db redis rabbitmq -d

# Seed inicial (idempotente)
python scripts/seed.py

# API con hot-reload
uvicorn app.main:app --reload --port 8000

# Tests con coverage
pytest tests/ -v --cov=app --cov-report=term-missing

# Verificar importaciones críticas
python -c "from app.core.security import create_access_token; print('✅ security OK')"
python -c "from app.main import app; print('✅ main OK')"
```
