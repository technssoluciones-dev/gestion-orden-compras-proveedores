"""
ProcureFlow AI — Security Module
JWT authentication, password hashing, token management
OWASP-aligned security practices
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config.settings import settings
from app.core.exceptions import AuthenticationException


# Password hashing context (bcrypt)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.bcrypt_rounds,
)

# Token types
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def hash_password(plain_password: str) -> str:
    """Hash a plain password using bcrypt."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: User ID or email
        extra_claims: Additional JWT claims (roles, permissions, etc.)

    Returns:
        Signed JWT string
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "type": ACCESS_TOKEN_TYPE,
        "iat": datetime.now(timezone.utc),
        "exp": expire,
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(subject: str) -> str:
    """Create a JWT refresh token with extended expiry."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )

    payload = {
        "sub": str(subject),
        "type": REFRESH_TOKEN_TYPE,
        "iat": datetime.now(timezone.utc),
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.

    Raises:
        AuthenticationException: If token is invalid, expired, or malformed
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        raise AuthenticationException(f"Invalid token: {str(e)}")


def get_token_subject(token: str) -> str:
    """Extract the subject (user ID) from a token."""
    payload = decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise AuthenticationException("Token missing subject claim")
    return sub


def verify_token_type(token: str, expected_type: str) -> Dict[str, Any]:
    """Verify token and check its type."""
    payload = decode_token(token)
    token_type = payload.get("type")
    if token_type != expected_type:
        raise AuthenticationException(
            f"Invalid token type: expected '{expected_type}', got '{token_type}'"
        )
    return payload


def sanitize_input(value: str, max_length: int = 500) -> str:
    """Basic input sanitization to prevent injection attacks."""
    if not isinstance(value, str):
        return str(value)
    # Strip control characters, limit length
    sanitized = "".join(c for c in value if ord(c) >= 32)
    return sanitized[:max_length].strip()
