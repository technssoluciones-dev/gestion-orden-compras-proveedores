Archivos movidos aquí por actualizacion_proyecto.py
Fecha: 2026-05-11T10:21:02.120395

ESTOS ARCHIVOS NO DEBEN ESTAR EN LA RAÍZ DEL PROYECTO.
Están archivados para referencia. Eliminables con seguridad.

Razones:
  logging.py: CRÍTICO: hace shadow del stdlib logging, rompe asyncio/structlog/fastapi
  security.py: Importa app.config.settings (no existe). Reemplazado por app/core/security.py
  settings.py: Importa app.config.settings (no existe). Reemplazado por app/core/config.py
  base.py: Duplicado de app/core/base.py
  db_models.py: Duplicado de app/domain/models/db_models.py
  exceptions.py: Duplicado de app/core/exceptions.py