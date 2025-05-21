import os
from typing import List
from xml.etree import ElementTree as ET

__FILE_DIR__ = os.path.dirname(__file__)

class EventArg:
    def __init__(self, name: str, type: str):
        self.name = name
        self.type = type

    def __repr__(self):
        return f"EventArg(name={self.name}, type={self.type})"


class Event:
    def __init__(self, name: str, id: str, args: List[EventArg]):
        self.name = name
        self.id = int(id, 16)
        self.args = args

    def __repr__(self):
        return f"Event(name={self.name}, id={self.id}, args={self.args})"


class EventsType:
    def __init__(self, xml_path: str):
        self.events : dict[int, Event] = {}
        self.__load_events(xml_path)

    def __load_events(self, xml_path: str):
        tree = ET.parse(xml_path)
        root = tree.getroot()
        for namespace in root.findall('namespace'):
            self.__parse_namespace(namespace, namespace.get('name'))

    def __parse_namespace(self, namespace : ET.Element[str], namespace_name: str):
        for sub_namespace in namespace.findall('namespace'):
            self.__parse_namespace(
                sub_namespace,
                f"{namespace_name}.{sub_namespace.get('name')}"
            )
        for event in namespace.findall('event'):
            event_name = f"{namespace_name}.{event.get('name')}"
            event_id = event.get('id')
            if not event_id:
                raise ValueError(f"Event {event_name} does not have an ID")
            args = [
                EventArg(arg.get('name'), arg.get('type'))
                for arg in event.find('args').findall('arg')
            ]
            self.events[event_id] = Event(event_name, event_id, args)

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


Events = EventsType(
    os.path.join(
        __FILE_DIR__,
        "events.xml"
    )
)
