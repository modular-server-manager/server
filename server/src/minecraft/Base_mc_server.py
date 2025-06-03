from abc import ABC, abstractmethod
from enum import IntEnum

from gamuLogger import Logger

from ..bus import Bus, BusData, Events

Logger.set_module("mc_server.base")

class ServerStatus(IntEnum):
    STOPPED = 0
    STARTING = 1
    RUNNING = 2
    STOPPING = 3
    ERROR = 4

class BaseMcServer(ABC):
    """
    Base class for Minecraft servers.
    This class is used to define the basic structure and functionality of a Minecraft server.
    """

    available_callbacks = {
        "on_server_stop": "SERVER.STOP",
        "on_server_seed": "SERVER.SEED",
        "on_console_send_message": "CONSOLE.SEND_MESSAGE",
        "on_console_send_command": "CONSOLE.SEND_COMMAND",
        "on_player_kick": "PLAYER.KICK",
        "on_player_ban": "PLAYER.BAN",
        "on_player_pardon": "PLAYER.PARDON",
        "on_player_list": "PLAYER.LIST",
    }

    def __init__(self, name : str, path : str, bus_data : BusData):
        self.__bus = Bus(bus_data)
        self.__name = name
        self.__path = path
        self.__register_callbacks()

    @abstractmethod
    def start(self) -> None:
        """
        Start the Minecraft server.
        This method should be implemented by subclasses to start the server.
        """
        pass

    @property
    def name(self) -> str:
        return self.__name

    @property
    def path(self) -> str:
        return self.__path

    def __on_ping(self, timestamp: int, server_name: str) -> bool:
        """
        Callback for the SERVER.PING event.
        This method can be overridden by subclasses to handle the ping event.
        """
        if server_name == self.name:
            Logger.info(f"Server {self.name} received ping at {timestamp}.")
        return True

    def __register_callbacks(self):
        for callback_name, event_name in self.available_callbacks.items():
            if hasattr(self, callback_name):
                event = Events[event_name]
                self.__bus.register(event, getattr(self, callback_name))
            else:
                Logger.warning(f"Callback {callback_name} not found in {self.__class__.__name__}. Skipping registration.")
                continue
        # Register the ping callback
        self.__bus.register(Events["SERVER.PING"], self.__on_ping)


def main():
    from datetime import datetime

    # example usage
    class ExampleServer(BaseMcServer):
        def on_server_start(self, timestamp: int, server_name: str) -> None:
            if server_name == self.name:
                #start the server
                print(f"Server started at {timestamp}")

    srv = ExampleServer("TestServer", "/path/to/server")

    Bus().trigger(Events["SERVER.START"], int(datetime.now().timestamp()), "TestServer")
