import threading as th
import time
from datetime import datetime
from multiprocessing import shared_memory as shm
from typing import Any, Callable

from gamuLogger import Logger
from singleton import Singleton

from ..utils.misc import is_types_equals
from .bus_data import BusData
from .events import Event, Events

Logger.set_module("bus")

type Callback = Callable[..., Any]


class Bus(Singleton):

    def __init__(self, data : BusData):
        if hasattr(self, "_Bus__subscribers"):
            return # avoid reinitializing

        self.__shared_list_write = data.write_list    # write messages to the bus
        self.__shared_list_read = data.read_list      # read messages from the bus

        self.__memory_size = data.memory_size
        self.__empty_string = data.empty_string  # Define an empty string of max length
        self.__max_string_length = data.max_string_length

        self.__listen = False
        self.__thread = th.Thread(target=self.__read_incoming, daemon=True, name="BusListener")

        self.__subscribers: dict[int, list[Callback]] = {}
        Logger.info("Bus initialized")

    def __str__(self):
        return f"Bus(subscribers={self.__subscribers})"

    def __repr__(self):
        return f"Bus(subscribers={self.__subscribers})"

    def __move_forward(self):
        for i in range(len(self.__shared_list_read) - 1):
            self.__shared_list_read[i] = self.__shared_list_read[i+1]
            self.__shared_list_read[-1] = self.__empty_string

    def __check_callback(self, event: Event, callback: Callback):

        annotations = callback.__annotations__
        if "return" not in annotations:
            raise ValueError(f"Callback for event {event.name} is missing return type annotation")
        if not is_types_equals(str(annotations["return"]), event.return_type):
            raise ValueError(f"Callback for event {event.name} should return {event.return_type} (got {annotations['return']})")
        for arg in event.args:
            if arg.name not in annotations:
                raise ValueError(f"Callback for event {event.name} is missing argument {arg.name}")
            if not is_types_equals(str(annotations[arg.name].__name__), arg.type):
                raise ValueError(f"Callback for event {event.name} has argument {arg.name} with wrong type (expected {arg.type}, got {annotations[arg.name].__name__})")
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

    def __register(self, event: Event, callback: Callback):
        if event.id not in self.__subscribers:
            self.__subscribers[event.id] = []
        self.__subscribers[event.id].append(callback)
        Logger.debug(f"Subscribed to event {event.name} with callback {callback.__name__}")

    def register(self, event: Event, callback: Callback):
        self.__check_callback(event, callback)
        self.__register(event, callback)

    def unregister(self, event: Event, callback: Callback):
        if event.id in self.__subscribers:
            if callback in self.__subscribers[event.id]:
                self.__subscribers[event.id].remove(callback)
                Logger.debug(f"Unsubscribed from event {event.name} with callback {callback.__name__}")
            else:
                Logger.warning(f"Callback {callback.__name__} not found for event {event.name}")
        else:
            Logger.warning(f"No subscribers for event {event.name}")

    def clear(self):
        self.__subscribers.clear()
        Logger.debug("Cleared all subscribers")

    def get_subscribers(self, event_id: int) -> list[Callback]:
        return self.__subscribers[event_id] if event_id in self.__subscribers else []

    def trigger(self, event: Event, **kwargs: Any) -> Any:
        """
        Trigger an event with the given name and arguments.
        If the event requires a timestamp and it is not provided, it will be added automatically.
        Returns the result of the first callback that returns a non-None value.
        """
        if "timestamp" not in kwargs:
            for a in event.args:
                if a.name == "timestamp" and a.type == "int":
                    kwargs["timestamp"] = int(datetime.now().timestamp())

        encoded = Event.encode(event, **kwargs)
        if len(encoded) > self.__max_string_length:
            raise ValueError(f"Encoded event data exceeds memory size limit: {len(encoded)} bytes > {self.__max_string_length} bytes")
        Logger.debug(f"Triggering event {event.name} with arguments: {kwargs}")
        Logger.trace(f"Encoded data: {encoded} (Length: {len(encoded)} bytes)")
        for i in range(len(self.__shared_list_write)):
            if self.__shared_list_write[i] == self.__empty_string:
                self.__shared_list_write[i] = encoded
                break
        else:
            raise ValueError("No free position in shared list to send data.")

        if event.return_type != None:
            res = self.wait_for(event.return_event(), timeout=5)  # Wait for the event to be processed and return the result
            Logger.debug(f"Event {event.name} triggered, waiting for result. Received: {res}")
            return res['result'] if res is not None else None
        else:
            Logger.debug(f"Event {event.name} triggered without return type, no waiting for result.")
            return None

    def __read_incoming(self):
        Logger.info("Bus listening started")
        while self.__listen:
            msg = self.__shared_list_read[0]
            if msg != self.__empty_string:
                try:
                    event, args = Event.decode(msg)
                    Logger.debug(f"Received message: {event} with args: {args}")
                    Logger.trace(f"Raw data: {msg} (Length: {len(msg)} bytes)")
                    if event.id in self.__subscribers:
                        for callback in self.__subscribers[event.id]:
                            result = callback(**args)
                            Logger.debug(f"Callback {callback.__name__} returned: {result}")
                            if result is not None and event.return_type != "None":
                                self.trigger(event.return_event(), result=result)
                except Exception as e:
                    Logger.error(f"Error processing message {event} with {args}: {e}")
            self.__move_forward()
            time.sleep(0.01)
        Logger.info("Bus listening stopped")

    def wait_for(self, event: Event, timeout: float = -1) -> Any:
        """
        create a temporary listener for the given event and wait for it to be triggered.
        timeout is in seconds, -1 means no timeout.
        """
        result = None
        def wait_for_callback(**kwargs) -> None:
            nonlocal result
            result = kwargs

        self.__register(event, wait_for_callback)

        start_time = time.time()
        while result is None:
            if timeout > 0 and time.time() - start_time > timeout:
                Logger.warning(f"Timeout waiting for event {event.name}, returning None")
                break
            time.sleep(0.01)

        self.unregister(event, wait_for_callback)
        return result

    def start(self):
        if not self.__listen:
            self.__listen = True
            self.__thread.start()
        else:
            Logger.warning("Bus is already listening")

    def stop(self):
        if self.__listen:
            self.__listen = False
            self.__thread.join()
        else:
            Logger.warning("Bus is not listening")












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
    print(bus2.trigger(Events["PLAYERS.LIST"], timestamp=int(datetime.now().timestamp()), server_name="TestServer2"))
