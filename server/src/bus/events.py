import os
import sys
from datetime import datetime
from json import dumps as json_dumps
from json import loads as json_loads
from typing import Any, Callable, List
from xml.etree import ElementTree as ET

from gamuLogger import Logger
from version import Version

from ..utils.regex import (RE_DICT_TYPE, RE_LIST_TYPE, RE_TUPLE_TYPE,
                        RE_ENCODED_DICT, RE_ENCODED_LIST, RE_ENCODED_TUPLE)
from ..utils.misc import split_with_nested

Logger.set_module("Bus.Events")

__FILE_DIR__ = os.path.dirname(__file__)


#used in composite arguments encoding
NEGATIVE_ACKNOWLEDGE = "\x15"  # ASCII Negative Acknowledge (NAK) character
SYNCHRONOUS_IDLE = "\x16"  # ASCII Synchronous Idle (SYN) character
END_OF_TRANSMISSION_BLOCK = "\x17"  # ASCII End of Transmission Block (ETB) character
CANCEL = "\x18"  # ASCII Cancel (CAN) character
END_OF_MEDIUM = "\x19"  # ASCII End of Medium (EM) character

#used in the encoding of events and their arguments
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
    
def guess_type(data: Any) -> str:
    original_type = type(data).__name__
    guessed_type = original_type
    if original_type == "dict": # explore dict to find key and value types
        if data:
            key_types = set()
            value_types = set()
            for key, value in data.items():
                key_types.add(guess_type(key))
                value_types.add(guess_type(value))
            if len(key_types) == 1:
                key_type = key_types.pop()
            else:
                key_type = '|'.join(sorted(key_types))
            if len(value_types) == 1:
                value_type = value_types.pop()
            else:
                value_type = '|'.join(sorted(value_types))
            guessed_type = f"dict[{key_type}, {value_type}]"
        else:
            guessed_type = "dict" # empty dict, cannot guess types
    elif original_type == "list": # explore list to find item type
        if data:
            item_types = set(guess_type(item) for item in data)
            if len(item_types) == 1:
                item_type = item_types.pop()
            else:
                item_type = '|'.join(sorted(item_types))
            guessed_type = f"list[{item_type}]"
        else:
            guessed_type = "list" # empty list, cannot guess type
    elif original_type == "tuple": # explore tuple to find item types
        if data:
            item_types = [guess_type(item) for item in data]
            guessed_type = f"tuple[{', '.join(item_types)}]"  
        else:  
            guessed_type = "tuple" # empty tuple, cannot guess types
    Logger.trace(f"Guessed type {original_type} -> {guessed_type}")
    return guessed_type

def encode(data : Any, data_type : str) -> str:
    """
    Encodes data into a string based on its type.
    """
    Logger.trace(f"Encoding data: {data}\nas type: {data_type}")
    if data_type == "int":
        return str(int(data))
    elif data_type == "float":
        return str(float(data))
    elif data_type in ("str", "string"):
        return str(data)
    elif data_type == "Version":
        if not isinstance(data, Version):
            raise TypeError("Expected a Version instance")
        return str(data)
    elif data_type == "bool":
        return "t" if data else "f"
    elif data_type == "datetime":
        if not isinstance(data, datetime):
            raise TypeError("Expected a datetime instance")
        return str(int(data.timestamp()))
    elif match_res := RE_LIST_TYPE.match(data_type):
        if not isinstance(data, list):
            raise TypeError("Expected a list")
        item_type = match_res.group(1)
        result = "[" + NEGATIVE_ACKNOWLEDGE.join(
            encode(item, item_type.strip()) for item in data
        ) + "]"
        return result
    elif match_res := RE_TUPLE_TYPE.match(data_type):
        if not isinstance(data, tuple):
            raise TypeError("Expected a tuple")
        inner_types = split_with_nested(match_res.group(1))
        if len(inner_types) != len(data):
            raise ValueError(f"Expected a tuple of {len(inner_types)} elements, got {len(data)}")
        result = "(" + NEGATIVE_ACKNOWLEDGE.join(
            encode(item, item_type.strip()) for item, item_type in zip(data, inner_types)
        ) + ")"
        return result
    elif match_res := RE_DICT_TYPE.match(data_type):
        if not isinstance(data, dict):
            raise TypeError("Expected a dict")
        inner_types = split_with_nested(match_res.group(1))
        if len(inner_types) != 2:
            raise ValueError("Expected a dict with two types (key and value)")
        key_type = inner_types[0].strip()
        value_type = inner_types[1].strip()
        result = "{" + NEGATIVE_ACKNOWLEDGE.join(
            f"{encode(key, key_type)}{SYNCHRONOUS_IDLE}{encode(value, value_type)}"
            for key, value in data.items()
        ) + "}"
        return result
    elif data_type == "Any": # in that case, the type will be guessed from the data, then added as a prefix of the value
        guessed_type = guess_type(data)
        encoded_data = encode(data, guessed_type)
        return f"{guessed_type}{END_OF_MEDIUM}{encoded_data}"
    else:
        raise ValueError(f"Unknown data type: {data_type}")


def decode(data: str, data_type: str) -> Any:
    """
    Decodes a string into data based on its type.
    """
    
    if data_type == "Any": # in that case, the type is prefixed to the data, separated by END_OF_MEDIUM
        if END_OF_MEDIUM not in data:
            raise ValueError("Expected type prefix in data for 'Any' type")
        type_prefix, actual_data = data.split(END_OF_MEDIUM, 1)
        return decode(actual_data, type_prefix)
    
    Logger.trace(f"Decoding data: {data}\nas type: {data_type}")
    if data_type == "int":
        return int(data)
    elif data_type == "float":
        return float(data)
    elif data_type in ("str", "string"):
        return data
    elif data_type == "Version":
        return Version.from_string(data)
    elif data_type == "bool":
        if data not in ("t", "f"):
            raise ValueError("Expected 't' or 'f' for bool type")
        return data == "t"
    elif data_type == "datetime":
        return datetime.fromtimestamp(int(data))
    elif match_res := RE_LIST_TYPE.match(data_type):
        item_type = match_res.group(1)
        if not (match := RE_ENCODED_LIST.match(data)):
            raise ValueError(f"Expected an encoded list for data: {data}")
        items_str = split_with_nested(match.group(1), NEGATIVE_ACKNOWLEDGE) if match.group(1) else []
        return [
            decode(item_str, item_type.strip()) for item_str in items_str
        ]
    elif match_res := RE_TUPLE_TYPE.match(data_type):
        inner_types = split_with_nested(match_res.group(1))
        if not (match := RE_ENCODED_TUPLE.match(data)):
            raise ValueError(f"Expected an encoded tuple for data: {data}")
        items_str = split_with_nested(match.group(1), NEGATIVE_ACKNOWLEDGE) if match.group(1) else []
        if len(inner_types) != len(items_str):
            raise ValueError(f"Expected a tuple of {len(inner_types)} elements, got {len(items_str)}")
        return tuple(
            decode(item_str, item_type.strip()) for item_str, item_type in zip(items_str, inner_types)
        )
    elif match_res := RE_DICT_TYPE.match(data_type):
        inner_types = split_with_nested(match_res.group(1))
        if len(inner_types) != 2:
            raise ValueError("Expected a dict with two types (key and value)")
        key_type = inner_types[0].strip()
        value_type = inner_types[1].strip()
        if not (match := RE_ENCODED_DICT.match(data)):
            raise ValueError(f"Expected an encoded dict for data: {data}")
        items_str = split_with_nested(match.group(1), NEGATIVE_ACKNOWLEDGE) if match.group(1) else []
        result = {}
        for item_str in items_str:
            if SYNCHRONOUS_IDLE not in item_str:
                raise ValueError(f"Malformed dict item: {item_str}")
            key_str, value_str = item_str.split(SYNCHRONOUS_IDLE, 1)
            key = decode(key_str, key_type)
            value = decode(value_str, value_type)
            result[key] = value
        return result
    else:
        raise ValueError(f"Unknown data type: {data_type}")
        
        

class EventArg:
    # type_map : dict[str, tuple[Callable[[str], Any], Callable[[Any], str]]] = { # from_string, to_string
    #     "int":          (int, str),
    #     "float":        (float, str),
    #     "str":          (str, str),
    #     "string":       (str, str),
    #     "Version":      (Version.from_string, str),
    #     "bool":         (lambda s: s == "t", lambda v: "t" if v else "f"),
    #     "datetime":     (lambda s: datetime.fromtimestamp(int(s)), lambda v: str(int(v.timestamp()))),
    #     "__default":    (json_loads, lambda d: json_dumps(d, ensure_ascii=False, separators=(',', ':'), default=str))
    # }
                

    def __init__(self, name: str, type: str, id : int):
        self.name = name
        self.type = type
        self.id = id

    def __repr__(self):
        return f"EventArg(name={self.name}, type={self.type}, id={self.id})"

    def __str__(self):
        return f"{self.name}: {self.type}"

    # def convert(self, value: str):
    #     if self.type in self.type_map:
    #         from_string, _ = self.type_map[self.type]
    #     else:
    #         Logger.warning(f"Unknown type {self.type} for argument {self.name}, using default JSON deserializer")
    #         from_string, _ = self.type_map["__default"]
    #     try:
    #         return from_string(value)
    #     except Exception as e:
    #         raise TypeError(f"Failed to convert value '{value}' to type {self.type} for argument {self.name}: {e}") from e

    # def to_string(self, value: Any) -> str:
    #     if self.type in self.type_map:
    #         _, to_string = self.type_map[self.type]
    #     else:
    #         Logger.warning(f"Unknown type {self.type} for argument {self.name}, using default JSON serializer")
    #         _, to_string = self.type_map["__default"]
    #     try:
    #         return to_string(value)
    #     except Exception as e:
    #         raise TypeError(f"Failed to convert value '{value}' to string for argument {self.name}: {e}") from e
    
    def convert(self, value: str) -> Any:
        try:
            return decode(value, self.type)
        except Exception as e:
            raise TypeError(f"Failed to convert value '{value}' to type {self.type} for argument {self.name}: {e}") from e
    def to_string(self, value: Any) -> str:
        try:
            return encode(value, self.type)
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

class EventsType:

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
            self.__parse_namespace(namespace, namespace.get('name') or "global")
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
            event_id = int(event.get('id'), 16) #type: ignore
            if not event_id:
                raise ValueError(f"Event {event_name} does not have an ID")
            args = [
                EventArg(arg.get('name'), arg.get('type'), int(arg.get('id', 0), 16)) #type: ignore
                for arg in event.find('args').findall('arg') #type: ignore
            ]

            return_type = event.find('return').get('type') #type: ignore
            Logger.debug(f"Registering event: {event_name} (ID: {event_id})")
            if event_id in self.events:
                Logger.warning(f"Event ID {event_id} already exists, overwriting: {self.events[event_id].name} -> {event_name}")
            self.events[event_id] = Event(event_name, event_id, args, return_type) #type: ignore

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
