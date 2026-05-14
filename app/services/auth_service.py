"""Authentication Service."""
import uuid as _uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import verify_password, create_access_token, create_refresh_token, verify_token_type
from app.core.exceptions import AuthenticationException
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse
import structlog

logger = structlog.get_logger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def login(self, credentials: LoginRequest) -> TokenResponse:
        user = await self.user_repo.get_by_email(credentials.email)
        if not user or not verify_password(credentials.password, user.hashed_password):
            raise AuthenticationException("Invalid email or password")
        if not user.is_active:
            raise AuthenticationException("Account is disabled")

        extra_claims = {"role": user.role.value, "email": user.email}
        access_token = create_access_token(str(user.id), extra_claims)
        refresh_token = create_refresh_token(str(user.id))

        await self.user_repo.update(user.id, {"last_login_at": datetime.now(timezone.utc)})
        logger.info("user_login", user_id=str(user.id), email=user.email)

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = verify_token_type(refresh_token, "refresh")
        subject = payload.get("sub")

        # CRÍTICO v5: JWT 'sub' es str — convertir a UUID igual que en deps.py.
        # Sin esta conversión, repo.get_by_id() recibe un str y PostgreSQL
        # rechaza la query con "invalid input syntax for type uuid".
        try:
            user_id = _uuid.UUID(str(subject))
        except (ValueError, AttributeError):
            raise AuthenticationException("Invalid subject in refresh token")

        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise AuthenticationException("Invalid refresh token")

        extra_claims = {"role": user.role.value, "email": user.email}
        new_access  = create_access_token(str(user.id), extra_claims)
        new_refresh = create_refresh_token(str(user.id))
        return TokenResponse(access_token=new_access, refresh_token=new_refresh)
