"""User management routes."""
import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import hash_password
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.api.deps import CurrentUser, require_role
from app.domain.models.db_models import UserRole

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    """Retorna el perfil del usuario autenticado."""
    return current_user


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def create_user(
    payload: UserCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Crea un nuevo usuario. Requiere rol ADMIN.

    SECURITY: Sin este guard, cualquier persona podría registrarse
    como ADMIN desde la API pública.
    """
    repo = UserRepository(db)
    existing = await repo.get_by_email(payload.email)
    if existing:
        from app.core.exceptions import EntityAlreadyExistsException
        raise EntityAlreadyExistsException("User", "email", payload.email)
    data = payload.model_dump(exclude={"password"})
    data["hashed_password"] = hash_password(payload.password)
    return await repo.create(data)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    from app.core.exceptions import EntityNotFoundException
    user = await repo.get_by_id(user_id)
    if not user:
        raise EntityNotFoundException("User", user_id)
    return user
