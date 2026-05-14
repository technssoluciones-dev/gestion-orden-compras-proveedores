"""
ProcureFlow AI — app/config package (compatibility shim).

La configuración vive en app.core.config.
Este módulo redirige imports legacy para evitar ImportError.

Fix v6: app/config/__init__.py estaba vacío. Si algún archivo futuro
intenta `from app.config import settings`, este shim lo resuelve
sin romper la arquitectura.
"""
from app.core.config import settings, get_settings  # noqa: F401
