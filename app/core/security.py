"""
ProcureFlow AI — Security Module
JWT authentication, password hashing, token management
OWASP-aligned security practices

Fix v6: archivo original solo tenía hash/verify_password.
        Las funciones JWT faltantes causaban ImportError en startup.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import AuthenticationException

# ── Password hashing ───────────────────────────────────────────────────────
# bcrypt_rounds viene de settings (.env BCRYPT_ROUNDS). Default 12.
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.bcrypt_rounds,
)

# ── Token type constants ───────────────────────────────────────────────────
ACCESS_TOKEN_TYPE  = "access"
REFRESH_TOKEN_TYPE = "refresh"


def hash_password(password: str) -> str:
    """Hash a plain password using bcrypt."""
    if not password:
        raise ValueError("Password vacío")
    password = password.strip()
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password excede límite bcrypt de 72 bytes")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject:      User ID (UUID string)
        extra_claims: Additional JWT claims (role, email, etc.)
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload: Dict[str, Any] = {
        "sub":  str(subject),
        "type": ACCESS_TOKEN_TYPE,
        "iat":  datetime.now(timezone.utc),
        "exp":  expire,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    """Create a signed JWT refresh token with extended expiry."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    payload = {
        "sub":  str(subject),
        "type": REFRESH_TOKEN_TYPE,
        "iat":  datetime.now(timezone.utc),
        "exp":  expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.

    Raises:
        AuthenticationException: if token is invalid, expired, or malformed.
    """
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as e:
        raise AuthenticationException(f"Invalid token: {e}")


def get_token_subject(token: str) -> str:
    """Extract the subject (user ID) from a decoded token."""
    payload = decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise AuthenticationException("Token missing subject claim")
    return sub


def verify_token_type(token: str, expected_type: str) -> Dict[str, Any]:
    """Decode token and assert its type matches expected_type."""
    payload = decode_token(token)
    token_type = payload.get("type")
    if token_type != expected_type:
        raise AuthenticationException(
            f"Invalid token type: expected '{expected_type}', got '{token_type}'"
        )
    return payload


def sanitize_input(value: str, max_length: int = 500) -> str:
    """Strip control characters and enforce length limit."""
    if not isinstance(value, str):
        return str(value)
    sanitized = "".join(ch for ch in value if ord(ch) >= 32)
    return sanitized[:max_length].strip()
