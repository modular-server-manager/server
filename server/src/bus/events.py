import os
import sys
from datetime import datetime
from json import dumps as json_dumps
from json import loads as json_loads
from typing import Any, Callable, List
from xml.etree import ElementTree as ET

from gamuLogger import Logger
from singleton import Singleton
from version import Version

Logger.set_module("Bus.Events")

__FILE_DIR__ = os.path.dirname(__file__)

FILE_SEPARATOR = "\x1c"    # ASCII File Separator (FS) character
GROUP_SEPARATOR = "\x1d"   # ASCII Group Separator (GS) character
RECORD_SEPARATOR = "\x1e"  # ASCII Record Separator (RS) character
UNIT_SEPARATOR = "\x1f"    # ASCII Unit Separator (US) character



class EncodedEvent:
    def __init__(self, encoded_event: str):
        self.__string = encoded_event

    def __str__(self):
        return ' '.join(format(ord(c), '02X') for c in self.__string)

    def __repr__(self):
        return f"EncodedEvent({self.__string})"

    def __eq__(self, value):
        if isinstance(value, EncodedEvent):
            return self.__string == value.__string
        elif isinstance(value, str):
            return self.__string == value
        return False

    def string(self) -> str:
        """
        Returns the encoded event string.
        """
        return self.__string

    def __len__(self) -> int:
        """
        Returns the length of the encoded event string.
        """
        return len(self.__string)

    @staticmethod
    def create(event: 'Event', **kwargs) -> 'EncodedEvent':
        """
        Creates an EncodedEvent instance from an Event and its arguments.
        """
        result = f"{event.id:05x}{FILE_SEPARATOR}"
        args_list : list[str] = []
        for arg in event.args:
            if arg.name not in kwargs:
                raise ValueError(f"Missing argument {arg.name} for event {event.name}")
            value = kwargs[arg.name]

            value = arg.to_string(value)

            args_list.append(f"{arg.id:02x}{RECORD_SEPARATOR}{value}")
        result += GROUP_SEPARATOR.join(args_list)
        return EncodedEvent(result)

    @staticmethod
    def from_hex_string(hex_string: str) -> 'EncodedEvent':
        """
        Creates an EncodedEvent instance from a hexadecimal string.
        The string should be a valid hexadecimal representation of the encoded event.
        """
        if not isinstance(hex_string, str):
            raise TypeError("Expected a string")
        try:
            decoded_string = bytes.fromhex(hex_string).decode('utf-8')
        except ValueError as e:
            raise ValueError(f"Invalid hexadecimal string: {e}") from e
        return EncodedEvent(decoded_string)

    def decode(self) -> tuple['Event', dict[str, Any]]:
        """
        Decodes the encoded event string into an Event instance and a dictionary of arguments.
        """
        parts = self.__string.split(FILE_SEPARATOR)
        if len(parts) < 2:
            raise ValueError("Encoded event string is malformed")
        if len(parts) == 4:
            # Handle the case where the string is in the format "source_id:02X{FILE_SEPARATOR}target_id:02X{FILE_SEPARATOR}event_id:02X{FILE_SEPARATOR}args"
            source_id, target_id, event_id_hex, args_str = parts
            parts = parts[2:]  # Keep only the event ID and args

        event_id = int(parts[0], 16)
        args_str = parts[1].split(GROUP_SEPARATOR)

        event = Events.get_event(event_id)

        args = {}
        for arg_str in args_str:
            if not arg_str:
                continue
            arg_parts = arg_str.split(RECORD_SEPARATOR)
            if len(arg_parts) != 2:
                raise ValueError(f"Malformed argument string: {arg_str}")
            arg_id = int(arg_parts[0], 16)
            value = arg_parts[1]
            for arg in event.args:
                if arg.id == arg_id:
                    typed_value = arg.convert(value)
                    args[arg.name] = typed_value
                    break
            else:
                raise KeyError(f"Argument with ID {arg_id} not found in event {event.name}")
        return event, args

class EventArg:
    type_map : dict[str, tuple[Callable[[str], Any], Callable[[Any], str]]] = { # from_string, to_string
        "int":          (int, str),
        "float":        (float, str),
        "str":          (str, str),
        "string":       (str, str),
        "Version":      (Version.from_string, str),
        "bool":         (lambda s: s == "t", lambda v: "t" if v else "f"),
        "datetime":    (lambda s: datetime.fromtimestamp(int(s)), lambda v: str(int(v.timestamp()))),
        "__default":    (json_loads, lambda v: json_dumps(v, ensure_ascii=False, separators=(',', ':'), default=str))
    }

    def __init__(self, name: str, type: str, id : int):
        self.name = name
        self.type = type
        self.id = id

    def __repr__(self):
        return f"EventArg(name={self.name}, type={self.type}, id={self.id})"

    def __str__(self):
        return f"{self.name}: {self.type}"

    def convert(self, value: str):
        if self.type in self.type_map:
            from_string, _ = self.type_map[self.type]
        else:
            from_string, _ = self.type_map["__default"]
        try:
            return from_string(value)
        except Exception as e:
            raise TypeError(f"Failed to convert value '{value}' to type {self.type} for argument {self.name}: {e}") from e

    def to_string(self, value: Any) -> str:
        if self.type in self.type_map:
            _, to_string = self.type_map[self.type]
        else:
            _, to_string = self.type_map["__default"]
        try:
            return to_string(value)
        except Exception as e:
            raise TypeError(f"Failed to convert value '{value}' to string for argument {self.name}: {e}") from e

class Event:
    def __init__(self, name: str, id: int, args: List[EventArg], return_type: str):
        self.name = name
        self.id = id
        self.args = args
        self.return_type = return_type

    def return_event(self):
        """
        Returns a new Event instance that represents the return type of this event.
        """
        if self.id > 65535 or self.name.endswith(".RETURN"):
            raise ValueError(
                f"Event {self.name} is already a return event or has an ID that exceeds the maximum allowed value."
            )

        if self.return_type == "None":
            raise ValueError(
                f"Event {self.name} does not have a return type defined."
            )

        return Event(
            name=f"{self.name}.RETURN",
            id=self.id + 65536,  # Increment ID by 65536 so in hexa : 0x0209 (0x00209) will be 0x10209
            args=[EventArg(name="result", type=self.return_type, id=1)],
            return_type="None"
        )

    def __repr__(self):
        return f"Event(name={self.name}, id={self.id}, args={self.args}, return_type={self.return_type})"

    def __str__(self):
        args_str = ", ".join(str(arg) for arg in self.args)
        return f"{self.name}({args_str}) -> {self.return_type}"

    def __iter__(self):
        return iter(self.args)

    def __getitem__(self, item: str):
        for arg in self.args:
            if arg.name == item:
                return arg
        raise KeyError(f"Argument {item} not found in event {self.name}")

    @staticmethod
    def encode(event : 'Event', **kwargs) -> EncodedEvent:
        """
        Encodes an event and its arguments into a string format.
        The format is:
        <event_id><FILE_SEPARATOR><arg_id1><RECORD_SEPARATOR><value1><GROUP_SEPARATOR><arg_id2><RECORD_SEPARATOR><value2>...
        """
        if not isinstance(event, Event):
            raise TypeError("Expected an instance of Event")
        return EncodedEvent.create(event, **kwargs)

    @staticmethod
    def decode(encoded: EncodedEvent) -> tuple['Event', dict[str, str]]:
        """
        Decodes an encoded event string into an Event instance and a dictionary of arguments.
        The format is:
        <event_id><FILE_SEPARATOR><arg_id1><RECORD_SEPARATOR><value1><GROUP_SEPARATOR><arg_id2><RECORD_SEPARATOR><value2>...
        """
        return encoded.decode()

class EventsType(Singleton):

    def __init__(self, xml_path: str):
        self.events : dict[int, Event] = {}
        self.__load_events(xml_path)

    def __load_events(self, xml_path: str):
        Logger.info(f"Loading events from XML file: {xml_path}")
        try:
            tree = ET.parse(xml_path)
        except ET.ParseError as e:
            raise ValueError(f"Failed to parse XML file {xml_path}: {e}") from None
        root = tree.getroot()
        for namespace in root.findall('namespace'):
            self.__parse_namespace(namespace, namespace.get('name'))
        Logger.info(f"Loaded {len(self.events)} events from XML file.")

    def __parse_namespace(self, namespace : ET.Element, namespace_name: str):
        Logger.debug(f"Parsing namespace: {namespace_name}")
        for sub_namespace in namespace.findall('namespace'):
            self.__parse_namespace(
                sub_namespace,
                f"{namespace_name}.{sub_namespace.get('name')}"
            )
        for event in namespace.findall('event'):
            event_name = f"{namespace_name}.{event.get('name')}"
            event_id = int(event.get('id'), 16)
            if not event_id:
                raise ValueError(f"Event {event_name} does not have an ID")
            args = [
                EventArg(arg.get('name'), arg.get('type'), int(arg.get('id', 0), 16))
                for arg in event.find('args').findall('arg')
            ]
            return_type = event.find('return').get('type')
            Logger.debug(f"Registering event: {event_name} (ID: {event_id})")
            if event_id in self.events:
                Logger.warning(f"Event ID {event_id} already exists, overwriting: {self.events[event_id].name} -> {event_name}")
            self.events[event_id] = Event(event_name, event_id, args, return_type)

    def __getitem__(self, item: str|int) -> Event:
        if isinstance(item, str):
            for event in self.events.values():
                if event.name == item:
                    return event
        elif isinstance(item, int):
            if item in self.events:
                return self.events[item]
        raise KeyError(f"Event {item} not found")

    def __contains__(self, item: str|int) -> bool:
        if isinstance(item, str):
            for event in self.events.values():
                if event.name == item:
                    return True
        elif isinstance(item, int):
            if item in self.events:
                return True
        return False

    def __iter__(self):
        return iter(self.events.values())

    def __len__(self):
        return len(self.events)

    def ids(self) -> List[int]:
        return list(self.events.keys())

    def get_event(self, event_id: int) -> Event:
        if event_id > 65535:
            return self.get_event(event_id - 65536).return_event()
        if event_id in self.events:
            return self.events[event_id]
        raise KeyError(f"Event {event_id} not found")


try:
    Events = EventsType(
        os.path.join(
            __FILE_DIR__,
            "events.xml"
        )
    )
except Exception as e:
    Logger.fatal(f"Failed to load events from XML file: {e}")
    sys.exit(1)
