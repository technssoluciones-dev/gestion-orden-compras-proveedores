"""
ProcureFlow AI — Base Domain Entity
DDD-aligned base class for all domain entities
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


def utcnow() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


@dataclass
class DomainEvent:
    """Base class for all domain events (Event-Driven Architecture)."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = field(default="")
    occurred_at: datetime = field(default_factory=utcnow)
    aggregate_id: str = field(default="")
    aggregate_type: str = field(default="")
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "payload": self.payload,
            "metadata": self.metadata,
        }


class AggregateRoot:
    """
    Base class for DDD Aggregate Roots.
    Tracks domain events for event-driven workflows.
    """

    def __init__(self):
        self._domain_events: List[DomainEvent] = []

    def add_domain_event(self, event: DomainEvent) -> None:
        """Register a domain event to be published."""
        self._domain_events.append(event)

    def pull_domain_events(self) -> List[DomainEvent]:
        """Consume and clear pending domain events."""
        events = list(self._domain_events)
        self._domain_events.clear()
        return events

    def has_domain_events(self) -> bool:
        return bool(self._domain_events)


class ValueObject:
    """Base class for DDD Value Objects (immutable, equality by value)."""

    def __eq__(self, other: Any) -> bool:
        if type(self) is not type(other):
            return False
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))
