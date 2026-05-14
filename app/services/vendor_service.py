"""Vendor Service."""
import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.vendor_repository import VendorRepository
from app.domain.models.db_models import Vendor, VendorStatus
from app.schemas.vendor import VendorCreate, VendorUpdate
from app.core.exceptions import EntityNotFoundException, EntityAlreadyExistsException
import structlog

logger = structlog.get_logger(__name__)


class VendorService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = VendorRepository(session)

    async def create(self, data: VendorCreate) -> Vendor:
        existing = await self.repo.get_by_code(data.vendor_code)
        if existing:
            raise EntityAlreadyExistsException("Vendor", "vendor_code", data.vendor_code)
        vendor = await self.repo.create(data.model_dump())
        logger.info("vendor_created", vendor_id=str(vendor.id), code=data.vendor_code)
        return vendor

    async def get_by_id(self, vendor_id: uuid.UUID) -> Vendor:
        vendor = await self.repo.get_by_id(vendor_id)
        if not vendor or vendor.is_deleted:
            raise EntityNotFoundException("Vendor", vendor_id)
        return vendor

    async def list_active(self, skip: int = 0, limit: int = 50) -> List[Vendor]:
        """Returns only ACTIVE vendors (public supplier directory), paginado."""
        return await self.repo.get_active_vendors(skip=skip, limit=limit)

    async def list_all(self, skip: int = 0, limit: int = 50) -> List[Vendor]:
        """Returns all non-deleted vendors (for admin/manager views), paginado."""
        return await self.repo.get_all_vendors(skip=skip, limit=limit)

    async def update(self, vendor_id: uuid.UUID, data: VendorUpdate) -> Vendor:
        await self.get_by_id(vendor_id)  # raises 404 if not found / soft-deleted

        updated = await self.repo.update(vendor_id, data.model_dump(exclude_none=True))

        # v5 fix: BaseRepository.update() puede retornar None en race conditions.
        if updated is None:
            raise EntityNotFoundException("Vendor", vendor_id)

        logger.info("vendor_updated", vendor_id=str(vendor_id))
        return updated

    async def activate(self, vendor_id: uuid.UUID) -> Vendor:
        return await self.update(vendor_id, VendorUpdate(status=VendorStatus.ACTIVE))

    async def deactivate(self, vendor_id: uuid.UUID) -> Vendor:
        return await self.update(vendor_id, VendorUpdate(status=VendorStatus.INACTIVE))
