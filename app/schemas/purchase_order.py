"""Purchase Order schemas."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from app.schemas.common import BaseSchema
from app.domain.models.db_models import POStatus


class POLineItemCreate(BaseSchema):
    line_number: int
    description: str
    quantity: Decimal
    unit: Optional[str] = None
    unit_price: Decimal
    product_code: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None


class POLineItemResponse(BaseSchema):
    id: uuid.UUID
    line_number: int
    description: str
    quantity: Decimal
    unit: Optional[str]
    unit_price: Decimal
    total_price: Decimal
    product_code: Optional[str]
    received_quantity: Decimal


class PurchaseOrderCreate(BaseSchema):
    title: str
    description: Optional[str] = None
    priority: str = "normal"
    vendor_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    budget_id: Optional[uuid.UUID] = None
    required_by: Optional[datetime] = None
    currency: str = "USD"
    notes: Optional[str] = None
    line_items: List[POLineItemCreate] = []


class PurchaseOrderUpdate(BaseSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    vendor_id: Optional[uuid.UUID] = None
    required_by: Optional[datetime] = None
    notes: Optional[str] = None


class PurchaseOrderResponse(BaseSchema):
    id: uuid.UUID
    po_number: str
    title: str
    status: POStatus
    priority: str
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    currency: str
    requester_id: uuid.UUID
    vendor_id: Optional[uuid.UUID]
    department_id: Optional[uuid.UUID]
    required_by: Optional[datetime]
    ai_category: Optional[str]
    ai_risk_flag: bool
    created_at: datetime
    line_items: List[POLineItemResponse] = []
