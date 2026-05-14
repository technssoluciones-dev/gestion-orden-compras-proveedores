"""Vendor schemas."""
import uuid
from datetime import datetime
from typing import Optional
from app.schemas.common import BaseSchema
from app.domain.models.db_models import VendorStatus


class VendorCreate(BaseSchema):
    name: str
    legal_name: Optional[str] = None
    vendor_code: str
    tax_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    address_line1: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    payment_terms: int = 30
    currency: str = "USD"
    category: Optional[str] = None
    notes: Optional[str] = None


class VendorUpdate(BaseSchema):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[VendorStatus] = None
    payment_terms: Optional[int] = None
    category: Optional[str] = None
    notes: Optional[str] = None


class VendorResponse(BaseSchema):
    id: uuid.UUID
    name: str
    vendor_code: str
    email: Optional[str]
    status: VendorStatus
    payment_terms: int
    currency: str
    category: Optional[str]
    ai_risk_score: Optional[float]
    rating: Optional[float]
    created_at: datetime
