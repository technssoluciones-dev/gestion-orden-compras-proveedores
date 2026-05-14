"""
Pytest configuration and shared fixtures.

NOTA TÉCNICA: Usamos SQLite in-memory (aiosqlite) para tests unitarios e
integración por velocidad. Los modelos usan postgresql.UUID(as_uuid=True)
que SQLAlchemy mapea automáticamente a String en SQLite.

Fix v7: eliminado el fixture custom event_loop que estaba deprecado en
pytest-asyncio 0.23.7 y se convierte en error en 0.24+. La scope de sesión
se configura ahora en pytest.ini con asyncio_default_fixture_loop_scope.

Para tests 100% PostgreSQL-compatibles (CI/CD), usar TestContainers:
  pip install testcontainers[postgres]
  # y cambiar TEST_DB_URL por la URL del contenedor
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db
from app.domain.models.db_models import Base

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Motor SQLite compartido por toda la sesión de tests."""
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncSession:
    """
    Sesión de test con rollback automático después de cada test.
    Garantiza aislamiento sin recrear la DB entera.
    """
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """
    AsyncClient con override de get_db apuntando a la sesión de test.

    IMPORTANTE: el override NO hace commit para no interferir con el
    rollback de aislamiento. El test puede llamar db_session.flush()
    cuando necesite visibilidad de cambios dentro del mismo test.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
