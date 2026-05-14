"""Vendor Repository."""
import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.db_models import Vendor, VendorStatus
from app.repositories.base_repository import BaseRepository


class VendorRepository(BaseRepository[Vendor]):
    def __init__(self, session: AsyncSession):
        super().__init__(Vendor, session)

    async def get_by_code(self, vendor_code: str) -> Optional[Vendor]:
        """
        Busca vendor por código excluyendo soft-deleted.
        Fix v5: sin is_deleted=False, un vendor eliminado bloqueaba la creación
        de uno nuevo con el mismo código (409 fantasma).
        """
        result = await self.session.execute(
            select(Vendor).where(
                Vendor.vendor_code == vendor_code,
                Vendor.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def get_active_vendors(self, skip: int = 0, limit: int = 50) -> List[Vendor]:
        """Solo vendors ACTIVE — directorio público de proveedores."""
        result = await self.session.execute(
            select(Vendor)
            .where(
                Vendor.status == VendorStatus.ACTIVE,
                Vendor.is_deleted == False,
            )
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_all_vendors(self, skip: int = 0, limit: int = 50) -> List[Vendor]:
        """Todos los vendors no eliminados — para vistas admin/manager."""
        result = await self.session.execute(
            select(Vendor)
            .where(Vendor.is_deleted == False)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
