from argparse import ArgumentParser
from datetime import datetime
from typing import Any

from gamuLogger import Logger, Levels
Logger.set_level("stdout", Levels.WARNING)

from .bus import EncodedEvent, Event, events
from .bus.bus_data import BusMessagePrefix
from .bus.events import FILE_SEPARATOR


def decode_event(decoded_string: str) -> tuple[Event, dict[str, Any]]:
    """
    Decodes a hexadecimal string into an Event instance and a dictionary of arguments.

    :param hexa_string: The hexadecimal string to decode.
    :return: A tuple containing the Event instance and a dictionary of arguments.
    """
    if not isinstance(decoded_string, str):
        raise TypeError("Expected a string")

    return EncodedEvent(decoded_string).decode()


def any_to_string(value: Any) -> str:
    """
    Converts any value to a string representation.

    :param value: The value to convert.
    :return: The string representation of the value.
    """
    if isinstance(value, str):
        return value
    elif isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(value, list):
        return "[" + ", ".join(any_to_string(item) for item in value) + "]"
    elif isinstance(value, dict):
        return "{" + ", ".join(f"{any_to_string(k)}: {any_to_string(v)}" for k, v in value.items()) + "}"
    elif isinstance(value, tuple):
        return "(" + ", ".join(any_to_string(item) for item in value) + ")"
    elif isinstance(value, set):
        return "{" + ", ".join(any_to_string(item) for item in value) + "}"
    elif isinstance(value, type):
        return value.__name__
    elif hasattr(value, '__name__'):
        return value.__name__
    elif hasattr(value, '__str__'):
        return value.__str__()
    elif hasattr(value, '__repr__'):
        return value.__repr__()
    else:
        raise TypeError(f"Unsupported type: {type(value)}")


def print_event(event: Event, args: dict[str, Any]) -> None:
    """
    Prints the event and its arguments in a readable format.

    :param event: The Event instance.
    :param args: A dictionary of arguments for the event.
    """
    print(f"Event: {event.name} (ID: {event.id})")
    print("  Arguments:")
    for arg_name, arg_value in args.items():
        print(f"    {arg_name}: {any_to_string(arg_value)}")
    print(f"  Return type: {event.return_type}")


def print_prefix(prefix: BusMessagePrefix) -> None:
    """
    Prints the bus message prefix in a readable format.

    :param prefix: The BusMessagePrefix instance.
    """
    print(f"Prefix: {prefix}")
    print(f"  Source ID: {prefix.source_id}")
    print(f"  Target ID: {prefix.target_id}")
    print(f"  Fragment Number: {prefix.fragment_number}")
    print(f"  Fragment Count: {prefix.fragment_count}")
    print(f"  Message ID: {prefix.message_id}")
    

def main() -> None:
    parser = ArgumentParser(description="Decode a hexadecimal event string.")
    parser.add_argument("hexa_string", type=str, help="The hexadecimal string to decode.")
    parser.add_argument("--prefix", "-p", action="store_true", help="enable if the string contains a prefix")
    args = parser.parse_args()

    try:
        
        hexa_string = args.hexa_string.strip()
        decoded_string = bytes.fromhex(hexa_string).decode('utf-8')
        if args.prefix:
            prefix_str, decoded_string = decoded_string.split(FILE_SEPARATOR, 1)
            prefix = BusMessagePrefix.from_string(prefix_str)
            print_prefix(prefix)
        event, event_args = decode_event(decoded_string)
        print_event(event, event_args)
    except Exception as e:
        print(f"Error decoding event: {e}")


if __name__ == "__main__":
    main()
