"""
ProcureFlow AI — Domain & Application Exceptions
Clean, typed exceptions aligned with DDD principles
"""
from typing import Any, Dict, Optional


class ProcureFlowException(Exception):
    """Base exception for all ProcureFlow errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


# ── Domain Exceptions ──────────────────────────────────────────────────────────

class DomainException(ProcureFlowException):
    """Business rule violation."""
    def __init__(self, message: str, code: str = "DOMAIN_ERROR", details: Optional[Dict] = None):
        super().__init__(message, code=code, status_code=422, details=details)


class EntityNotFoundException(ProcureFlowException):
    """Entity not found in repository."""
    def __init__(self, entity: str, identifier: Any):
        super().__init__(
            message=f"{entity} with id '{identifier}' not found",
            code="ENTITY_NOT_FOUND",
            status_code=404,
            details={"entity": entity, "id": str(identifier)},
        )


class EntityAlreadyExistsException(ProcureFlowException):
    """Entity already exists."""
    def __init__(self, entity: str, field: str, value: Any):
        super().__init__(
            message=f"{entity} with {field}='{value}' already exists",
            code="ENTITY_ALREADY_EXISTS",
            status_code=409,
            details={"entity": entity, "field": field, "value": str(value)},
        )


class InvalidStatusTransitionException(DomainException):
    """Invalid state machine transition."""
    def __init__(self, entity: str, from_status: str, to_status: str):
        super().__init__(
            message=f"Cannot transition {entity} from '{from_status}' to '{to_status}'",
            code="INVALID_STATUS_TRANSITION",
            details={"from": from_status, "to": to_status},
        )


class InsufficientBudgetException(DomainException):
    """Budget limit exceeded."""
    def __init__(self, requested: float, available: float, currency: str = "USD"):
        super().__init__(
            message=f"Insufficient budget: requested {currency} {requested:.2f}, available {currency} {available:.2f}",
            code="INSUFFICIENT_BUDGET",
            details={"requested": requested, "available": available, "currency": currency},
        )


class ApprovalLimitExceededException(DomainException):
    """User's approval authority exceeded."""
    def __init__(self, amount: float, limit: float):
        super().__init__(
            message=f"Approval amount {amount:.2f} exceeds your authority limit {limit:.2f}",
            code="APPROVAL_LIMIT_EXCEEDED",
            details={"amount": amount, "limit": limit},
        )


class DuplicatePurchaseOrderException(DomainException):
    """Duplicate purchase order detected."""
    def __init__(self, reference: str):
        super().__init__(
            message=f"Purchase order with reference '{reference}' already exists",
            code="DUPLICATE_PO",
            details={"reference": reference},
        )


# ── Application Exceptions ─────────────────────────────────────────────────────

class AuthenticationException(ProcureFlowException):
    """Authentication failure."""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code="AUTHENTICATION_FAILED", status_code=401)


class AuthorizationException(ProcureFlowException):
    """Authorization failure (forbidden)."""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, code="FORBIDDEN", status_code=403)


class ValidationException(ProcureFlowException):
    """Input validation error."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, code="VALIDATION_ERROR", status_code=422, details=details)


class ExternalServiceException(ProcureFlowException):
    """External service integration error."""
    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"External service '{service}' error: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details={"service": service},
        )


class RateLimitException(ProcureFlowException):
    """Rate limit exceeded."""
    def __init__(self):
        super().__init__(
            "Rate limit exceeded. Please try again later.",
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
        )


class ConflictException(ProcureFlowException):
    """Resource conflict."""
    def __init__(self, message: str):
        super().__init__(message, code="CONFLICT", status_code=409)
