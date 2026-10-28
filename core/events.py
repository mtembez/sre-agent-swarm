"""Asynchronous event emitter and broadcast bus for real-time agent telemetry."""

import asyncio
from typing import Any, Callable, Coroutine, Dict, List
import logging

logger = logging.getLogger(__name__)


class EventBus:
    """Singleton async event broadcaster for decoupling agent steps from API streams."""

    _instance = None

    @classmethod
    def get_instance(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._listeners: List[Callable[[Dict[str, Any]], Coroutine]] = []
        self._history: List[Dict[str, Any]] = []

    def subscribe(self, callback: Callable[[Dict[str, Any]], Coroutine]):
        """Subscribe async callback to all emitted events."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def unsubscribe(self, callback: Callable[[Dict[str, Any]], Coroutine]):
        """Remove subscriber."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    async def emit(self, event_type: str, data: Dict[str, Any]):
        """Broadcast event to all registered listeners asynchronously."""
        payload = {"event": event_type, "data": data}
        self._history.append(payload)

        coros = []
        for listener in self._listeners:
            try:
                coros.append(listener(payload))
            except Exception as exc:
                logger.warning("Listener dispatch error: %s", exc)

        if coros:
            await asyncio.gather(*coros, return_exceptions=True)

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self._history)

    def clear(self):
        self._history.clear()
