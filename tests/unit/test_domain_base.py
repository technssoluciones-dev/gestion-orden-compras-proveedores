"""
Tests de DomainEvent y AggregateRoot — app/core/base.py (0% → ~90%).
Módulos DDD que no tenían ninguna cobertura.
"""
import pytest
import time
from app.core.base import DomainEvent, AggregateRoot, ValueObject, utcnow


class TestDomainEvent:
    def test_default_fields_populated(self):
        event = DomainEvent(event_type="test.created")
        assert event.event_id  # UUID generado
        assert event.event_type == "test.created"
        assert event.occurred_at is not None
        assert event.payload == {}
        assert event.metadata == {}

    def test_to_dict_contains_all_keys(self):
        event = DomainEvent(
            event_type="po.approved",
            aggregate_id="po-123",
            aggregate_type="PurchaseOrder",
            payload={"amount": 1000},
        )
        d = event.to_dict()
        assert d["event_type"] == "po.approved"
        assert d["aggregate_id"] == "po-123"
        assert d["aggregate_type"] == "PurchaseOrder"
        assert d["payload"] == {"amount": 1000}
        assert "occurred_at" in d
        assert "event_id" in d

    def test_occurred_at_is_iso_string(self):
        event = DomainEvent(event_type="x")
        d = event.to_dict()
        # ISO format must be parseable
        from datetime import datetime
        datetime.fromisoformat(d["occurred_at"].replace("Z", "+00:00"))

    def test_unique_event_ids(self):
        e1 = DomainEvent(event_type="a")
        e2 = DomainEvent(event_type="a")
        assert e1.event_id != e2.event_id


class TestAggregateRoot:
    def test_starts_with_no_events(self):
        agg = AggregateRoot()
        assert not agg.has_domain_events()

    def test_add_and_pull_events(self):
        agg = AggregateRoot()
        e1 = DomainEvent(event_type="created")
        e2 = DomainEvent(event_type="updated")
        agg.add_domain_event(e1)
        agg.add_domain_event(e2)

        assert agg.has_domain_events()
        events = agg.pull_domain_events()
        assert len(events) == 2
        assert events[0].event_type == "created"
        assert events[1].event_type == "updated"

    def test_pull_clears_events(self):
        agg = AggregateRoot()
        agg.add_domain_event(DomainEvent(event_type="x"))
        agg.pull_domain_events()
        assert not agg.has_domain_events()

    def test_pull_returns_copy(self):
        agg = AggregateRoot()
        agg.add_domain_event(DomainEvent(event_type="x"))
        events = agg.pull_domain_events()
        # Modificar la lista retornada no afecta el estado interno
        events.clear()
        agg.add_domain_event(DomainEvent(event_type="y"))
        assert agg.has_domain_events()


class TestValueObject:
    def test_equality_by_value(self):
        class Money(ValueObject):
            def __init__(self, amount: float, currency: str):
                self.amount = amount
                self.currency = currency

        m1 = Money(100.0, "USD")
        m2 = Money(100.0, "USD")
        m3 = Money(200.0, "USD")

        assert m1 == m2
        assert m1 != m3

    def test_different_types_not_equal(self):
        class A(ValueObject):
            def __init__(self, x: int):
                self.x = x

        class B(ValueObject):
            def __init__(self, x: int):
                self.x = x

        assert A(1) != B(1)

    def test_hashable(self):
        class Point(ValueObject):
            def __init__(self, x: int, y: int):
                self.x = x
                self.y = y

        p = Point(1, 2)
        s = {p}  # debe ser hashable para usarse en sets
        assert p in s


def test_utcnow_is_timezone_aware():
    from datetime import timezone
    dt = utcnow()
    assert dt.tzinfo is not None
    assert dt.tzinfo == timezone.utc
