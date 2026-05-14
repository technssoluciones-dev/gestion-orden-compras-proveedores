"""User schemas."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import EmailStr
from app.schemas.common import BaseSchema
from app.domain.models.db_models import UserRole


class UserCreate(BaseSchema):
    email: EmailStr
    username: str
    full_name: str
    password: str
    role: UserRole = UserRole.REQUESTER
    department_id: Optional[uuid.UUID] = None


class UserUpdate(BaseSchema):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    department_id: Optional[uuid.UUID] = None
    approval_limit: Optional[Decimal] = None
    is_active: Optional[bool] = None


class UserResponse(BaseSchema):
    id: uuid.UUID
    email: str
    username: str
    full_name: str
    role: UserRole
    department_id: Optional[uuid.UUID]
    approval_limit: Decimal
    is_active: bool
    is_verified: bool
    created_at: datetime
