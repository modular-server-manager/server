import os
from typing import List
from xml.etree import ElementTree as ET

from singleton import Singleton

__FILE_DIR__ = os.path.dirname(__file__)

class EventArg:
    def __init__(self, name: str, type: str):
        self.name = name
        self.type = type

    def __repr__(self):
        return f"EventArg(name={self.name}, type={self.type})"

    def __str__(self):
        return f"{self.name}: {self.type}"


class Event:
    def __init__(self, name: str, id: int, args: List[EventArg], return_type: str):
        self.name = name
        self.id = id
        self.args = args
        self.return_type = return_type

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

class EventsType(Singleton):

    def __init__(self, xml_path: str):
        self.events : dict[int, Event] = {}
        self.__load_events(xml_path)

    def __load_events(self, xml_path: str):
        tree = ET.parse(xml_path)
        root = tree.getroot()
        for namespace in root.findall('namespace'):
            self.__parse_namespace(namespace, namespace.get('name'))

    def __parse_namespace(self, namespace : ET.Element, namespace_name: str):
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
                EventArg(arg.get('name'), arg.get('type'))
                for arg in event.find('args').findall('arg')
            ]
            return_type = event.find('return').get('type')
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
        if event_id in self.events:
            return self.events[event_id]
        raise KeyError(f"Event {event_id} not found")

Events = EventsType(
    os.path.join(
        __FILE_DIR__,
        "events.xml"
    )
)


if __name__ == "__main__":
    for e in Events:
        print(f"{e.id:<5d}\t{e}")
