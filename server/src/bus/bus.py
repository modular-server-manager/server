import threading as th
import time
from datetime import datetime
from typing import Any, Callable
import traceback
import random

from gamuLogger import Logger

from ..utils.misc import is_types_equals
from .bus_data import BusData, BusMessagePrefix
from .events import FILE_SEPARATOR, EncodedEvent, Event, Events

Logger.set_module("Bus.Interface")

type Callback = Callable[..., Any]


class Bus:

    def __init__(self, data : BusData):
        self.__shared_list_write = data.write_list    # write messages to the bus
        self.__shared_list_read = data.read_list      # read messages from the bus

        self.__write_list_lock = data.write_list_lock  # lock for writing to the bus
        self.__read_list_lock = data.read_list_lock    # lock for reading from the bus

        self.__memory_size = data.memory_size
        self.__empty_string = data.empty_string  # Define an empty string of max length
        self.__max_string_length = data.max_string_length
        self.__name = data.name
        self.__id = data.id

        self.__listen = False
        self.__thread = th.Thread(target=self.__read_incoming, daemon=True, name=f"BusListener_{data._for}")

        self.__subscribers: dict[int, list[Callback]] = {}
        Logger.info("Bus initialized")

    def __str__(self):
        return f"Bus(subscribers={self.__subscribers})"

    def __repr__(self):
        return f"Bus(subscribers={self.__subscribers})"

    def __move_forward(self):
        with self.__read_list_lock:
            for i in range(len(self.__shared_list_read) - 1):
                self.__shared_list_read[i] = self.__shared_list_read[i+1]
                self.__shared_list_read[-1] = self.__empty_string

    def __check_callback(self, event: Event, callback: Callback):

        annotations = callback.__annotations__
        if "return" in annotations:
            if isinstance(annotations["return"], type):
                return_str = annotations["return"].__name__
            else:
                return_str = str(annotations["return"])
        else:
            return_str = "None"
        if not is_types_equals(str(return_str), event.return_type):
            raise ValueError(f"Callback for event {event.name} should return {event.return_type} (got {return_str})")
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


    def __add_prefix(self, encoded: str, prefix : BusMessagePrefix) -> str:
        return f"{prefix}{FILE_SEPARATOR}{encoded}"

    def __read_prefix(self, encoded: str) -> tuple[BusMessagePrefix, str]:
        """
        Splits the encoded string into its prefix and data components.
        """
        prefix_str, data = encoded.split(FILE_SEPARATOR, 1)
        prefix = BusMessagePrefix.from_string(prefix_str)
        return prefix, data

    def __write(self, raw_msg: str, __to : int, fragment_number: int, fragment_count: int, msg_id : int):
        # add the id at the beginning, followed by a 0 for the target
        prefix = BusMessagePrefix(source_id=self.__id,
                                  target_id=__to,
                                  message_id=msg_id,
                                  fragment_number=fragment_number,
                                  fragment_count=fragment_count)
        encoded_str = self.__add_prefix(raw_msg, prefix)
        Logger.trace(f"Writing message (with prefix) to bus: {' '.join(format(ord(c), '02X') for c in encoded_str)} (Length: {len(encoded_str)} bytes)")

        if len(encoded_str) > self.__max_string_length:
            raise ValueError(f"Encoded event data exceeds memory size limit: {len(encoded_str)} bytes > {self.__max_string_length} bytes")

        with self.__write_list_lock:
            for i in range(len(self.__shared_list_write)):
                if self.__shared_list_write[i] == self.__empty_string:
                    self.__shared_list_write[i] = encoded_str
                    break
            else:
                raise ValueError("No free position in shared list to send data.")

    def __send(self, event: Event, __to : int, timeout : int = 5, **kwargs: Any) -> Any:
        if "timestamp" not in kwargs:
            for a in event.args:
                if a.name == "timestamp" and a.type == "datetime":
                    kwargs["timestamp"] = datetime.now()

        encoded = Event.encode(event, **kwargs)

        # if len(encoded) > self.__max_string_length:
        #     raise ValueError(f"Encoded event data exceeds memory size limit: {len(encoded)} bytes > {self.__max_string_length} bytes")
        Logger.debug(f"Triggering event {event.name} with arguments: {kwargs}")
        Logger.trace(f"Raw data: {encoded} (Length: {len(encoded)} bytes)")
        if len(encoded) + BusMessagePrefix.length() <= self.__max_string_length:
            parts = [encoded.string()]
        else:
            # Split the encoded string into fragments if it exceeds the max length
            parts = [encoded.string()[i:i + self.__max_string_length - BusMessagePrefix.length()] for i in range(0, len(encoded.string()), self.__max_string_length - BusMessagePrefix.length())]
            Logger.debug(f"Encoded event data split into {len(parts)} fragments due to size limit.")

        message_id = random.randint(0, 255)  # Generate a random message ID for the event

        for i, part in enumerate(parts):
            self.__write(part, __to, i, len(parts), message_id)

        if event.return_type != "None":
            res = self.wait_for(event.return_event(), timeout=timeout)  # Wait for the event to be processed and return the result
            res = res['result'] if res is not None else None
            Logger.debug(f"Event {event.name} returned: {res}")
            return res
        # res['result'] is of the type specified in the event's <return type="..." /> tag
        # or None if the timeout is reached or the event is not triggered
        else:
            Logger.debug(f"Event {event.name} triggered without return type, no waiting for result.")
            return None

    def trigger(self, event: Event, timeout : int = 5, **kwargs: Any) -> Any:
        """
        Trigger an event with the given name and arguments.
        If the event requires a timestamp and it is not provided, it will be added automatically.
        Returns the result of the first callback that returns a non-None value.
        """
        return self.__send(event, 0, timeout=timeout, **kwargs) # 0 mean everyone will receive the message

    def __read_incoming(self):
        Logger.info("Bus listening started")
        Logger.trace(f"bus hash: {self.__hash__()}\nthread name: {self.__thread.name}\nthread hash: {self.__thread.__hash__()}")
        buffer : dict[int, tuple[int, str]] = {} # msg_id : (remaining_fragment, raw_data)
        while self.__listen:
            try:
                with self.__read_list_lock:
                    raw = self.__shared_list_read[0]
                self.__move_forward()
                if raw == self.__empty_string:
                    time.sleep(0.01)
                    continue
                prefix, raw = self.__read_prefix(raw)
                if prefix.target_id not in (0, self.__id):
                    Logger.error(f"Received a message that is not for this bus (target_id={prefix.target_id:02X}, this bus id={self.__id:02X}), ignoring it.")
                    time.sleep(0.01)
                    continue
                if prefix.fragment_count == 1:
                    msg = EncodedEvent(raw)
                else:
                    if prefix.message_id not in buffer:
                        if prefix.fragment_number != 0:
                            Logger.error(f"Received a fragment with fragment_number={prefix.fragment_number} but no previous fragments for message_id={prefix.message_id}, ignoring it.")
                            time.sleep(0.01)
                            continue
                        buffer[prefix.message_id] = (prefix.fragment_count - 1, raw)
                    else:
                        remaining, data = buffer[prefix.message_id]
                        data += raw
                        remaining -= 1
                        if remaining == 0:
                            del buffer[prefix.message_id]
                            msg = EncodedEvent(data)
                        else:
                            buffer[prefix.message_id] = (remaining, data)
                            continue
            except TypeError:
                continue
            if msg != self.__empty_string:
                Logger.trace(f"Processing message: {msg}")
                try:
                    event, args = Event.decode(msg)
                    Logger.debug(f"Received message: {event} with args: {args}")
                    Logger.trace(f"Raw data: {msg} (Length: {len(msg)} bytes)")
                    if event.id in self.__subscribers:
                        def a():
                            try:
                                self.__exec_callback(event, prefix.source_id, **args)
                            except Exception as e:
                                Logger.error(f"Error processing event {event.name} with args {args}: {e.__class__.__name__} : {e}")
                                Logger.debug(traceback.format_exc())
                        t = th.Thread(target=a, daemon=True, name=f"BusCallback-{event.name}")
                        Logger.trace(f"Starting thread for event {event.name} with args {args}\nthread hash: {t.__hash__()}\nthread name: {t.name}")
                        t.start()
                    else:
                        Logger.debug(f"No subscribers for event {event.name}, skipping processing.")
                        Logger.trace(f"List of current subscribers:\n{'\n'.join(f"{Events.get_event(event).name} ({event}): {', '.join(callback.__name__ for callback in callbacks)}" for event, callbacks in self.__subscribers.items())}")
                except Exception as e:
                    Logger.error(f"Error processing message {event} with {args}: {e.__class__.__name__} : {e}")
            time.sleep(0.01)
        Logger.info("Bus listening stopped")

    def __exec_callback(self, event : Event, source_id : int, **args: Any) -> Any:
        for callback in self.__subscribers[event.id]:
            Logger.debug(f"Processing message {event} with callback {callback.__name__} and args {args}")
            result = callback(**args)
            Logger.debug(f"Callback {callback.__name__} returned: {result}")
            if result is not None and event.return_type != "None":
                self.__send(event.return_event(), source_id, result=result) # Send the result back to the source
                break  # Stop after the first callback that returns a non-None value

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
                Logger.warning(f"Timeout while waiting for event {event.name}, returning None")
                break
            time.sleep(0.01)

        self.unregister(event, wait_for_callback)
        return result

    def start(self):
        Logger.trace(f"Starting bus listener thread\nbus hash : {self.__hash__()}\nthread name : {self.__thread.name}\nthread hash : {self.__thread.__hash__()}")
        if not self.__listen and not self.__thread.is_alive():
            self.__listen = True
            try:
                self.__thread.start()
            except RuntimeError as e:
                Logger.error(f"Failed to start bus listener thread: {e}")
                Logger.trace(f"Thread:\n alive: {self.__thread.is_alive()}\n name: {self.__thread.name}\n hash: {self.__thread.__hash__()}\n repr: {self.__thread.__repr__()}")
                Logger.debug(traceback.format_exc())
                return
            Logger.info("Bus is now listening for events")
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

    def _get_players_1(timestamp: datetime, server_name: str) -> list[str]:
        if server_name == "TestServer":
            return ["Player1", "Player2", "Player3"]
        return None

    def _get_players_2(timestamp: datetime, server_name: str) -> list[str]:
        if server_name == "TestServer2":
            return ["Player4", "Player5", "Player6"]
        return None


    bus1.register(Events["PLAYERS.LIST"], _get_players_1)
    bus1.register(Events["PLAYERS.LIST"], _get_players_2)


    bus2 = Bus()
    print(bus2.trigger(Events["PLAYERS.LIST"], timestamp=datetime.now(), server_name="TestServer2"))
