from argparse import ArgumentParser
from datetime import datetime
from typing import Any

from .bus import EncodedEvent, Event, events


def decode_event(hexa_string: str) -> tuple[Event, dict[str, Any]]:
    """
    Decodes a hexadecimal string into an Event instance and a dictionary of arguments.

    :param hexa_string: The hexadecimal string to decode.
    :return: A tuple containing the Event instance and a dictionary of arguments.
    """
    if not isinstance(hexa_string, str):
        raise TypeError("Expected a string")

    return EncodedEvent.from_hex_string(hexa_string).decode()


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
    print("Arguments:")
    for arg_name, arg_value in args.items():
        print(f"  {arg_name}: {any_to_string(arg_value)}")
    print(f"Return type: {event.return_type}")

def main() -> None:
    parser = ArgumentParser(description="Decode a hexadecimal event string.")
    parser.add_argument("hexa_string", type=str, help="The hexadecimal string to decode.")
    args = parser.parse_args()

    try:
        event, event_args = decode_event(args.hexa_string)
        print_event(event, event_args)
    except Exception as e:
        print(f"Error decoding event: {e}")


if __name__ == "__main__":
    main()
