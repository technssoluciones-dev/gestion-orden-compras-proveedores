"""FastAPI Dependencies — DI for services and auth."""
import uuid as _uuid
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_token
from app.core.exceptions import AuthenticationException
from app.repositories.user_repository import UserRepository
from app.domain.models.db_models import User, UserRole

bearer_scheme = HTTPBearer()
DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DBSession,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    try:
        payload = decode_token(credentials.credentials)
        subject = payload.get("sub")
        if not subject:
            raise AuthenticationException()
        # CRÍTICO: JWT 'sub' es str — convertir a UUID antes de la query
        try:
            user_id = _uuid.UUID(str(subject))
        except ValueError:
            raise AuthenticationException("Invalid user ID in token")
    except AuthenticationException as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message)

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: UserRole):
    async def check(current_user: CurrentUser):
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return check
