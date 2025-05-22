from typing import Any, Callable, Dict

from events import Event, Events
from gamuLogger import Logger
from singleton import Singleton

Logger.set_module("bus")


type Callback = Callable[..., Any]


class Bus(Singleton):

    def __init__(self):
        if hasattr(self, "_Bus__subscribers"):
            return # avoid reinitializing

        self.__subscribers: dict[int, list[Callback]] = {}
        Logger.info("Bus initialized")

    def __check_callback(self, event: Event, callback: Callback):

        annotations = callback.__annotations__
        if "return" not in annotations or str(annotations["return"]) != event.return_type:
            raise ValueError(
                f"Callback for event {event.name} should return {event.return_type} (got {annotations.get('return', 'None')})"
            )
        for arg in event.args:
            if arg.name not in annotations:
                raise ValueError(
                    f"Callback for event {event.name} is missing argument {arg.name}"
                )
            if annotations[arg.name].__name__ != arg.type:
                raise ValueError(
                    f"Callback for event {event.name} has argument {arg.name} with wrong type (expected {arg.type}, got {annotations[arg.name].__name__})"
                )
        for arg_name, arg_type in annotations.items():
            if arg_name == "return":
                continue
            if arg_name not in (arg.name for arg in event.args):
                raise ValueError(
                    f"Callback for event {event.name} has extra argument {arg_name} (only {', '.join(arg.name for arg in event.args)} are allowed)"
                )
            if arg_type.__name__ != event[arg_name].type:
                raise ValueError(
                    f"Callback for event {event.name} has argument {arg_name} with wrong type (expected {event.args[arg_name].type}, got {arg_type.__name__})"
                )

    def register(self, event: Event, callback: Callback):
        self.__check_callback(event, callback)
        if event.id not in self.__subscribers:
            self.__subscribers[event.id] = []
        self.__subscribers[event.id].append(callback)
        Logger.debug(f"Subscribed to event {event.name} with callback {callback}")

    def unregister(self, event: Event, callback: Callback):
        if event.id in self.__subscribers:
            if callback in self.__subscribers[event.id]:
                self.__subscribers[event.id].remove(callback)
                Logger.debug(f"Unsubscribed from event {event.name} with callback {callback}")
            else:
                Logger.warning(f"Callback {callback} not found for event {event.name}")
        else:
            Logger.warning(f"No subscribers for event {event.name}")

    def trigger(self, event: Event, *args: Any) -> Any:
        if event.id in self.__subscribers:
            results : Any = None
            for callback in self.__subscribers[event.id]:
                try:
                    r = callback(*args)
                except Exception as e:
                    Logger.error(f"Error in callback {callback} for event {event.id}: {e}")
                else:
                    if r is not None:
                        if results is not None:
                            Logger.warning(f"Multiple callbacks for event {event.name} returned a value:\n{r}\n{results}\nkeeping the first one")
                        results = r
            return results
        else:
            Logger.warning(f"No subscribers for event {event.id}")
            return []

    def clear(self):
        self.__subscribers.clear()
        Logger.debug("Cleared all subscribers")

    def get_subscribers(self, event_id: int) -> list[Callback]:
        return self.__subscribers[event_id] if event_id in self.__subscribers else []


if __name__ == "__main__":
    from datetime import datetime
    bus1 = Bus()

    def _get_players_1(timestamp: int, server_name: str) -> list[str]:
        if server_name == "TestServer":
            return ["Player1", "Player2", "Player3"]
        return None

    def _get_players_2(timestamp: int, server_name: str) -> list[str]:
        if server_name == "TestServer2":
            return ["Player4", "Player5", "Player6"]
        return None


    bus1.register(Events["PLAYERS.LIST"], _get_players_1)
    bus1.register(Events["PLAYERS.LIST"], _get_players_2)


    bus2 = Bus()
    print(bus2.trigger(Events["PLAYERS.LIST"], int(datetime.now().timestamp()), "TestServer2"))
