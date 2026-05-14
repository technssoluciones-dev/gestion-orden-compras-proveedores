"""Simple in-process event bus for domain events."""
from typing import Callable, Dict, List, Type
from app.core.base import DomainEvent
import structlog

logger = structlog.get_logger(__name__)


class EventBus:
    _handlers: Dict[str, List[Callable]] = {}

    @classmethod
    def subscribe(cls, event_type: str, handler: Callable) -> None:
        cls._handlers.setdefault(event_type, []).append(handler)

    @classmethod
    async def publish(cls, event: DomainEvent) -> None:
        handlers = cls._handlers.get(event.event_type, [])
        logger.debug("event_published", event_type=event.event_type, handlers=len(handlers))
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error("event_handler_error", event_type=event.event_type, error=str(e))
