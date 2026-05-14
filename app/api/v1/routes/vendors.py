"""Vendor routes — CRUD completo con guards de rol y paginación."""
import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.vendor_service import VendorService
from app.schemas.vendor import VendorCreate, VendorUpdate, VendorResponse
from app.api.deps import CurrentUser, require_role
from app.domain.models.db_models import UserRole

router = APIRouter()


@router.get("", response_model=List[VendorResponse])
async def list_vendors(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Registros a omitir"),
    limit: int = Query(50, ge=1, le=200, description="Máximo de registros"),
):
    """
    Lista vendors con paginación.

    - ADMIN / MANAGER / FINANCE: ven todos los estados (including PENDING_REVIEW,
      INACTIVE, BLACKLISTED).
    - Resto de roles: solo ACTIVE vendors (directorio público de proveedores).

    Fix v6: añadida paginación skip/limit para evitar timeout en prod
            con miles de registros.
    """
    svc = VendorService(db)
    if current_user.role in (UserRole.ADMIN, UserRole.MANAGER, UserRole.FINANCE):
        return await svc.list_all(skip=skip, limit=limit)
    return await svc.list_active(skip=skip, limit=limit)


@router.post(
    "",
    response_model=VendorResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
)
async def create_vendor(
    payload: VendorCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Crea un vendor. Requiere rol ADMIN o MANAGER.

    Fix v6: el endpoint original no tenía guard de rol — cualquier usuario
    autenticado (incluso VIEWER o REQUESTER) podía crear vendors.
    Esto es un problema de seguridad crítico en un sistema de procurement.
    """
    svc = VendorService(db)
    return await svc.create(payload)


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = VendorService(db)
    return await svc.get_by_id(vendor_id)


@router.patch(
    "/{vendor_id}",
    response_model=VendorResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
)
async def update_vendor(
    vendor_id: uuid.UUID,
    payload: VendorUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Actualiza campos del vendor. Requiere ADMIN o MANAGER."""
    svc = VendorService(db)
    return await svc.update(vendor_id, payload)


@router.post(
    "/{vendor_id}/activate",
    response_model=VendorResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
)
async def activate_vendor(
    vendor_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Activa el vendor (→ ACTIVE). Requiere ADMIN o MANAGER."""
    svc = VendorService(db)
    return await svc.activate(vendor_id)


@router.post(
    "/{vendor_id}/deactivate",
    response_model=VendorResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
)
async def deactivate_vendor(
    vendor_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Desactiva el vendor (→ INACTIVE). Requiere ADMIN o MANAGER.

    Fix v6: VendorService.deactivate() existía pero no había endpoint expuesto.
    El par activate/deactivate es necesario para operaciones de procurement.
    """
    svc = VendorService(db)
    return await svc.deactivate(vendor_id)
