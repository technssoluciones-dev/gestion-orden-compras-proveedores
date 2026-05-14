"""
ProcureFlow AI — Database ORM Models
SQLAlchemy 2.0 — moved to app/domain/models/
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey,
    Index, Numeric, String, Text, Integer, JSON,
    UniqueConstraint, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SoftDeleteMixin:
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


# ── Enums ──────────────────────────────────────────────────────────────────────

class UserRole(str, PyEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    REQUESTER = "requester"
    APPROVER = "approver"
    FINANCE = "finance"
    VIEWER = "viewer"


class POStatus(str, PyEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ORDERED = "ordered"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class VendorStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_REVIEW = "pending_review"
    BLACKLISTED = "blacklisted"


class ApprovalStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DELEGATED = "delegated"
    EXPIRED = "expired"


class BudgetPeriod(str, PyEnum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class NotificationType(str, PyEnum):
    EMAIL = "email"
    PUSH = "push"
    SLACK = "slack"
    WEBHOOK = "webhook"


# ── Models ─────────────────────────────────────────────────────────────────────

class Department(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "departments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    cost_center: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    users: Mapped[List["User"]] = relationship("User", back_populates="department")
    budgets: Mapped[List["Budget"]] = relationship("Budget", back_populates="department")
    children: Mapped[List["Department"]] = relationship("Department")
    __table_args__ = (Index("ix_departments_code", "code"), Index("ix_departments_active", "is_active"),)


class User(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.REQUESTER)
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    approval_limit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0.00"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    preferences: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    department: Mapped[Optional["Department"]] = relationship("Department", back_populates="users")
    purchase_orders: Mapped[List["PurchaseOrder"]] = relationship("PurchaseOrder", back_populates="requester", foreign_keys="PurchaseOrder.requester_id")
    approvals: Mapped[List["ApprovalStep"]] = relationship("ApprovalStep", back_populates="approver")
    __table_args__ = (Index("ix_users_role", "role"), Index("ix_users_department", "department_id"),)


class Vendor(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "vendors"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    vendor_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    tax_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    address_line1: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[VendorStatus] = mapped_column(Enum(VendorStatus), default=VendorStatus.PENDING_REVIEW)
    payment_terms: Mapped[int] = mapped_column(Integer, default=30)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ai_risk_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    ai_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rating: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True)
    purchase_orders: Mapped[List["PurchaseOrder"]] = relationship("PurchaseOrder", back_populates="vendor")
    contacts: Mapped[List["VendorContact"]] = relationship("VendorContact", back_populates="vendor")
    __table_args__ = (Index("ix_vendors_code", "vendor_code"), Index("ix_vendors_status", "status"),)


class VendorContact(TimestampMixin, Base):
    __tablename__ = "vendor_contacts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="contacts")


class PurchaseOrder(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "purchase_orders"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    po_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[POStatus] = mapped_column(Enum(POStatus), default=POStatus.DRAFT, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0.00"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0.00"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0.00"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    requester_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True)
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    budget_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=True)
    required_by: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ordered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ai_risk_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ai_suggested_vendor: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    external_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attachments: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    requester: Mapped["User"] = relationship("User", back_populates="purchase_orders", foreign_keys=[requester_id])
    vendor: Mapped[Optional["Vendor"]] = relationship("Vendor", back_populates="purchase_orders")
    line_items: Mapped[List["POLineItem"]] = relationship("POLineItem", back_populates="purchase_order", cascade="all, delete-orphan")
    approval_steps: Mapped[List["ApprovalStep"]] = relationship("ApprovalStep", back_populates="purchase_order")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="purchase_order")
    __table_args__ = (
        Index("ix_po_status", "status"), Index("ix_po_requester", "requester_id"),
        Index("ix_po_number", "po_number"), Index("ix_po_created", "created_at"),
        CheckConstraint("total_amount >= 0", name="check_po_total_positive"),
    )


class POLineItem(TimestampMixin, Base):
    __tablename__ = "po_line_items"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="CASCADE"))
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    product_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=Decimal("0"))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="line_items")
    __table_args__ = (
        UniqueConstraint("purchase_order_id", "line_number", name="uq_po_line_number"),
        CheckConstraint("quantity > 0", name="check_qty_positive"),
    )


class ApprovalWorkflow(TimestampMixin, Base):
    __tablename__ = "approval_workflows"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    min_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0.00"))
    max_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    rules: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    steps: Mapped[List["ApprovalWorkflowStep"]] = relationship("ApprovalWorkflowStep", back_populates="workflow", order_by="ApprovalWorkflowStep.order")


class ApprovalWorkflowStep(TimestampMixin, Base):
    __tablename__ = "approval_workflow_steps"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("approval_workflows.id"))
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    approver_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approver_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    timeout_hours: Mapped[int] = mapped_column(Integer, default=72)
    workflow: Mapped["ApprovalWorkflow"] = relationship("ApprovalWorkflow", back_populates="steps")


class ApprovalStep(TimestampMixin, Base):
    __tablename__ = "approval_steps"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"))
    approver_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ApprovalStatus] = mapped_column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    decision_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="approval_steps")
    approver: Mapped["User"] = relationship("User", back_populates="approvals")
    __table_args__ = (Index("ix_approval_po", "purchase_order_id"), Index("ix_approval_status", "status"),)


class Budget(TimestampMixin, Base):
    __tablename__ = "budgets"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    department_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id"))
    period: Mapped[BudgetPeriod] = mapped_column(Enum(BudgetPeriod), default=BudgetPeriod.ANNUAL)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    fiscal_period: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    committed_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0.00"))
    spent_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    department: Mapped["Department"] = relationship("Department", back_populates="budgets")
    purchase_orders: Mapped[List["PurchaseOrder"]] = relationship("PurchaseOrder")

    @property
    def available_amount(self) -> Decimal:
        return self.total_amount - self.committed_amount

    @property
    def utilization_percent(self) -> float:
        if self.total_amount == 0:
            return 0.0
        return float((self.spent_amount / self.total_amount) * 100)


class Document(TimestampMixin, Base):
    __tablename__ = "documents"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    purchase_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    document_type: Mapped[str] = mapped_column(String(50), default="attachment")
    ai_extracted_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    purchase_order: Mapped[Optional["PurchaseOrder"]] = relationship("PurchaseOrder", back_populates="documents")


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    old_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    __table_args__ = (
        Index("ix_audit_user", "user_id"), Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_created", "created_at"),
    )


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), default=NotificationType.EMAIL)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (Index("ix_notification_user", "user_id"),)
