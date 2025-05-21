from typing import Any, Callable, Optional

from gamuLogger import Logger

from .events import Event, Events

Logger.set_module("bus")


class Bus:
    def __init__(self):
        self.__subscribers: dict[int, list[Callable[..., None]]] = {}


    def subscribe(self, event: Event, callback: Callable[..., None]) -> None:
        """
        Subscribe to an event.
        """
        if event.id not in self.__subscribers:
            self.__subscribers[event.id] = []
        self.__subscribers[event.id].append(callback)
        Logger.debug(f"Subscribed to event {event.name} with callback {callback}")

    def unsubscribe(self, event: Event, callback: Callable[..., None]) -> None:
        """
        Unsubscribe from an event.
        """
        if event.id not in self.__subscribers:
            raise ValueError(f"Event {event.name} has no subscribers")

        if callback not in self.__subscribers[event.id]:
            raise ValueError(f"Callback {callback} not subscribed to event {event.name}")

        self.__subscribers[event.id].remove(callback)
        if not self.__subscribers[event.id]:
            del self.__subscribers[event.id]
        Logger.debug(f"Unsubscribed from event {event.name} with callback {callback}")

    def trigger(self, event: Event, *args: Any) -> None:
        """
        Trigger an event.
        """
        if event.id not in self.__subscribers:
            Logger.warning(f"Event {event.name} has no subscribers")
            return

        Logger.debug(f"Triggering event {event.name} with args {args}")
        for callback in self.__subscribers[event.id]:
            callback(*args)
            Logger.trace(f"Triggered event {event.name} with args {args} for callback {callback}")
