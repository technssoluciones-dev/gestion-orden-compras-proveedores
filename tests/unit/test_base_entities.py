"""
Unit tests — app/core/base.py
Cubre DomainEvent, AggregateRoot y ValueObject.
"""
from app.core.base import DomainEvent, AggregateRoot, ValueObject, utcnow


# ── DomainEvent ────────────────────────────────────────────────────────────

def test_domain_event_defaults():
    ev = DomainEvent(event_type="order.created", aggregate_id="abc-123")
    assert ev.event_type == "order.created"
    assert ev.aggregate_id == "abc-123"
    assert ev.event_id is not None
    assert ev.occurred_at is not None


def test_domain_event_to_dict():
    ev = DomainEvent(
        event_type="po.approved",
        aggregate_id="po-1",
        aggregate_type="PurchaseOrder",
        payload={"status": "approved"},
    )
    d = ev.to_dict()
    assert d["event_type"] == "po.approved"
    assert d["aggregate_id"] == "po-1"
    assert d["payload"]["status"] == "approved"
    assert "occurred_at" in d


def test_domain_event_unique_ids():
    e1 = DomainEvent(event_type="x")
    e2 = DomainEvent(event_type="x")
    assert e1.event_id != e2.event_id


# ── AggregateRoot ──────────────────────────────────────────────────────────

def test_aggregate_root_add_and_pull_events():
    agg = AggregateRoot()
    assert not agg.has_domain_events()

    ev = DomainEvent(event_type="thing.happened")
    agg.add_domain_event(ev)
    assert agg.has_domain_events()

    events = agg.pull_domain_events()
    assert len(events) == 1
    assert events[0].event_type == "thing.happened"
    assert not agg.has_domain_events()  # consumido


def test_aggregate_root_pull_clears_list():
    agg = AggregateRoot()
    for i in range(5):
        agg.add_domain_event(DomainEvent(event_type=f"ev.{i}"))
    assert len(agg.pull_domain_events()) == 5
    assert len(agg.pull_domain_events()) == 0


# ── ValueObject ────────────────────────────────────────────────────────────

class Money(ValueObject):
    def __init__(self, amount: float, currency: str):
        self.amount = amount
        self.currency = currency


def test_value_object_equality_by_value():
    m1 = Money(100.0, "USD")
    m2 = Money(100.0, "USD")
    assert m1 == m2


def test_value_object_inequality():
    m1 = Money(100.0, "USD")
    m2 = Money(200.0, "USD")
    assert m1 != m2


def test_value_object_type_inequality():
    class OtherMoney:
        def __init__(self):
            self.amount = 100.0
            self.currency = "USD"

    m = Money(100.0, "USD")
    assert m != OtherMoney()


def test_value_object_hashable():
    m1 = Money(100.0, "USD")
    m2 = Money(100.0, "USD")
    s = {m1, m2}
    assert len(s) == 1


# ── utcnow ─────────────────────────────────────────────────────────────────

def test_utcnow_returns_aware_datetime():
    from datetime import timezone
    dt = utcnow()
    assert dt.tzinfo == timezone.utc
