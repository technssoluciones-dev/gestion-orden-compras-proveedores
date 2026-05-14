"""
Unit tests — app/events/event_bus.py
Cubre subscribe, publish y manejo de errores en handlers.
"""
import pytest
from app.events.event_bus import EventBus
from app.core.base import DomainEvent


@pytest.mark.asyncio
async def test_subscribe_and_publish():
    """Handler recibe el evento publicado."""
    received = []

    async def handler(event: DomainEvent):
        received.append(event.event_type)

    EventBus.subscribe("test.event", handler)
    event = DomainEvent(event_type="test.event", aggregate_id="agg-1")
    await EventBus.publish(event)
    assert "test.event" in received


@pytest.mark.asyncio
async def test_publish_multiple_handlers():
    """Múltiples handlers se invocan para el mismo tipo de evento."""
    calls = []

    async def h1(event):
        calls.append("h1")

    async def h2(event):
        calls.append("h2")

    EventBus.subscribe("multi.event", h1)
    EventBus.subscribe("multi.event", h2)
    await EventBus.publish(DomainEvent(event_type="multi.event"))
    assert "h1" in calls
    assert "h2" in calls


@pytest.mark.asyncio
async def test_publish_no_handlers():
    """Publicar sin handlers no lanza excepción."""
    await EventBus.publish(DomainEvent(event_type="orphan.event"))


@pytest.mark.asyncio
async def test_handler_error_does_not_propagate():
    """
    Si un handler falla, EventBus absorbe el error y continúa
    con los demás handlers (resiliencia de bus de eventos).
    """
    calls = []

    async def bad_handler(event):
        raise RuntimeError("handler crashed")

    async def good_handler(event):
        calls.append("good")

    EventBus.subscribe("resilient.event", bad_handler)
    EventBus.subscribe("resilient.event", good_handler)
    await EventBus.publish(DomainEvent(event_type="resilient.event"))
    assert "good" in calls
