"""
Development seed script — crea datos iniciales.
Idempotente: seguro de ejecutar múltiples veces.
"""

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
)

from app.core.config import settings
from app.core.security import hash_password

# IMPORTANTE:
# fuerza carga de TODOS los modelos
from app.domain.models.db_models import (
    Base,
    User,
    UserRole,
    Department,
    Vendor,
    VendorStatus,
)


async def create_tables(engine):
    """
    Crea todas las tablas registradas en SQLAlchemy metadata.
    """

    try:
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda sync_conn: Base.metadata.create_all(
                    bind=sync_conn,
                    checkfirst=True,
                )
            )

        print("✔ Schema verificado/creado correctamente.")

    except Exception as e:
        print(f"❌ Error creando tablas: {type(e).__name__}: {e}")
        raise


async def seed():

    engine = create_async_engine(
        settings.database_url,
        echo=True,  # cambiar a False en producción
        future=True,
    )

    # Crear tablas primero
    await create_tables(engine)

    factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    async with factory() as session:

        try:

            # =====================================================
            # DEPARTMENT
            # =====================================================

            result = await session.execute(
                text("""
                    SELECT id
                    FROM departments
                    WHERE code = 'TECH'
                    LIMIT 1
                """)
            )

            existing_dept = result.fetchone()

            if existing_dept:

                dept_id = existing_dept[0]
                print("ℹ Department TECH ya existe.")

            else:

                dept = Department(
                    id=uuid.uuid4(),
                    name="Technology",
                    code="TECH",
                    description="Technology Department",
                    is_active=True,
                )

                session.add(dept)

                await session.flush()

                dept_id = dept.id

                print("✔ Department TECH creado.")

            # =====================================================
            # ADMIN USER
            # =====================================================

            result = await session.execute(
                text("""
                    SELECT id
                    FROM users
                    WHERE email = 'admin@procureflow.com'
                    LIMIT 1
                """)
            )

            if result.fetchone():

                print("ℹ Usuario admin ya existe.")

            else:

                admin = User(
                    id=uuid.uuid4(),
                    email="admin@procureflow.com",
                    username="admin",
                    full_name="System Administrator",
                    hashed_password=hash_password("Admin1234!"),
                    role=UserRole.ADMIN,
                    department_id=dept_id,
                    is_active=True,
                    is_verified=True,
                )

                session.add(admin)

                print("✔ Usuario admin creado.")

            # =====================================================
            # REQUESTER USER
            # =====================================================

            result = await session.execute(
                text("""
                    SELECT id
                    FROM users
                    WHERE email = 'requester@procureflow.com'
                    LIMIT 1
                """)
            )

            if result.fetchone():

                print("ℹ Usuario requester ya existe.")

            else:

                requester = User(
                    id=uuid.uuid4(),
                    email="requester@procureflow.com",
                    username="requester",
                    full_name="Test Requester",
                    hashed_password=hash_password("Test1234!"),
                    role=UserRole.REQUESTER,
                    department_id=dept_id,
                    is_active=True,
                    is_verified=True,
                )

                session.add(requester)

                print("✔ Usuario requester creado.")

            # =====================================================
            # VENDOR
            # =====================================================

            result = await session.execute(
                text("""
                    SELECT id
                    FROM vendors
                    WHERE vendor_code = 'VND-001'
                    LIMIT 1
                """)
            )

            if result.fetchone():

                print("ℹ Vendor VND-001 ya existe.")

            else:

                vendor = Vendor(
                    id=uuid.uuid4(),
                    name="Tech Supplies SA",
                    vendor_code="VND-001",
                    email="sales@techsupplies.com",
                    status=VendorStatus.ACTIVE,
                    payment_terms=30,
                    currency="USD",
                    category="Technology",
                )

                session.add(vendor)

                print("✔ Vendor VND-001 creado.")

            # =====================================================
            # COMMIT
            # =====================================================

            await session.commit()

            print("\n✔ Seed completado.")
            print("Admin:     admin@procureflow.com / Admin1234!")
            print("Requester: requester@procureflow.com / Test1234!")

        except SQLAlchemyError as e:

            await session.rollback()

            print(f"\n❌ Error SQLAlchemy: {type(e).__name__}")
            print(str(e))

            raise

        except Exception as e:

            await session.rollback()

            print(f"\n❌ Error general: {type(e).__name__}")
            print(str(e))

            raise

        finally:

            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())