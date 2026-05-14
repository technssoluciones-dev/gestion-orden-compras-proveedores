"""
Unit tests — app/core/database.py
Cubre check_db_connection y get_db.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_check_db_connection_success():
    """check_db_connection devuelve True cuando la DB responde."""
    from app.core.database import check_db_connection
    # La DB de tests (SQLite in-memory) debería responder OK
    # Usamos un mock para no depender de infra real
    with patch("app.core.database.engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)
        mock_engine.connect = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_conn),
            __aexit__=AsyncMock(return_value=False),
        ))
        result = await check_db_connection()
    assert result is True


@pytest.mark.asyncio
async def test_check_db_connection_failure():
    """check_db_connection devuelve False ante excepción."""
    from app.core.database import check_db_connection
    with patch("app.core.database.engine") as mock_engine:
        mock_engine.connect.side_effect = Exception("DB unreachable")
        result = await check_db_connection()
    assert result is False


@pytest.mark.asyncio
async def test_get_db_yields_session():
    """get_db es un async generator que entrega AsyncSession."""
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.core.database import get_db
    async for session in get_db():
        assert isinstance(session, AsyncSession)
        break
