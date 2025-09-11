import time
from abc import ABC, abstractmethod
from datetime import datetime
from enum import IntEnum

from gamuLogger import Logger
from version import Version

from ..bus import Bus, BusData, Events

Logger.set_module("Base Server.Base")

class ServerStatus(IntEnum):
    STOPPED = 0
    STARTING = 1
    RUNNING = 2
    STOPPING = 3
    ERROR = 4
    UNKNOWN = 5

    @staticmethod
    def from_string(status: str) -> "ServerStatus":
        """
        Convert a string to a ServerStatus enum.
        :param status: The status as a string.
        :return: The corresponding ServerStatus enum.
        """
        status = status.upper()
        if status not in ServerStatus.__members__:
            raise ValueError(f"Invalid server status: {status}")
        return ServerStatus[status]

    def __bool__(self) -> bool:
        """
        Convert the ServerStatus to a boolean value.
        :return: True if the server is running or starting, False otherwise.
        """
        return self in (ServerStatus.RUNNING, ServerStatus.STARTING)

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
        "on_player_kick": "PLAYERS.KICK",
        "on_player_ban": "PLAYERS.BAN",
        "on_player_pardon": "PLAYERS.PARDON",
        "on_player_list": "PLAYERS.LIST",
        "on_started_at": "SERVER.STARTED_AT",
    }

    def __init__(self, name : str, path : str, ram : int, mc_version : Version, bus_data : BusData):
        self.__bus = Bus(bus_data)
        self._ram = ram
        self._mc_version = mc_version
        self.__name = name
        self.__path = path
        self._ServerStatus = ServerStatus.STOPPED
        self.__started_at : datetime = None
        self.__register_callbacks()

    @property
    def status(self) -> ServerStatus:
        """
        Get the current status of the server.
        """
        return self._ServerStatus

    def start(self) -> None:
        """
        Start the Minecraft server.
        This method should be implemented by subclasses to start the server.
        Wait for the server to stop
        """
        Logger.info(f"Starting server \"{self.name}\"...")
        self.__bus.start()
        self._start()
        while self._ServerStatus not in (ServerStatus.RUNNING, ServerStatus.ERROR):
            time.sleep(0.2)
        if self._ServerStatus == ServerStatus.ERROR:
            Logger.error(f"Server \"{self.name}\" failed to start.")
            return
        self.__bus.trigger(Events["SERVER.STARTED"], server_name = self.name)
        self.__started_at = datetime.now()
        self._after_start()
        Logger.info(f"Server \"{self.name}\" started")
        self.__wait_for_stop()
        Logger.info(f"Server \"{self.name}\" has stopped with status: {self._ServerStatus.name}")

    def __wait_for_stop(self) -> None:
        """
        Wait for the server to stop.
        This method should be called after the server has been stopped to ensure it has fully stopped.
        """
        while self.status not in (ServerStatus.STOPPED, ServerStatus.ERROR):
            try:
                time.sleep(0.5)  # Wait for the server to
            except KeyboardInterrupt:
                break


    def _start(self) -> None:
        """
        Abstract method to start the server.
        This method should be implemented by subclasses to start the server.
        """
        pass

    def _after_start(self) -> None:
        """
        Abstract method to perform actions after the server has started.
        This method should be implemented by subclasses to handle post-start actions.
        """
        pass

    def stop(self) -> None:
        """
        Stop the Minecraft server.
        This method should be implemented by subclasses to stop the server.
        """
        Logger.info(f"Stopping server \"{self.name}\"...")
        self._stop()
        while self._ServerStatus not in (ServerStatus.STOPPED, ServerStatus.ERROR):
            time.sleep(0.2)
        self.__bus.trigger(Events["SERVER.STOPPED"], server_name = self.name)
        self.__started_at = None
        self.__bus.stop()
        Logger.info(f"Server \"{self.name}\" stopped with status: {self._ServerStatus.name}")

    def _stop(self) -> None:
        """
        Abstract method to stop the server.
        This method should be implemented by subclasses to stop the server.
        """
        pass

    @property
    def name(self) -> str:
        return self.__name

    @property
    def path(self) -> str:
        return self.__path
    
    @property
    def started_at(self) -> datetime:
        """
        Get the datetime when the server was started.
        :return: The datetime when the server was started, or None if the server has not been started.
        """
        return self.__started_at

    def __on_ping(self, timestamp: datetime, server_name: str) -> str:
        """
        Callback for the SERVER.PING event.
        This method can be overridden by subclasses to handle the ping event.
        """
        if server_name == self.name:
            Logger.info(f"Server {self.name} received ping at {timestamp}.")
            return self.status.name
        Logger.debug(f"Ping received for server {server_name}, but this is not the current server ({self.name}). Ignoring.")

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

    def on_started_at(self, timestamp: datetime, server_name: str) -> datetime:
        """
        Callback for the STARTED_AT event.
        This method is called when the server starts and can be overridden by subclasses.
        :param timestamp: The timestamp when the server started.
        :param server_name: The name of the server.
        :return: The timestamp when the server started.
        """
        if server_name == self.name:
            return self.__started_at
        Logger.debug(f"Started at event received for server {server_name}, but this is not the current server ({self.name}). Ignoring.")
        return None


def main():
    from datetime import datetime

    # example usage
    class ExampleServer(BaseMcServer):
        def on_server_start(self, timestamp: datetime, server_name: str) -> None:
            if server_name == self.name:
                #start the server
                print(f"Server started at {timestamp}")

    srv = ExampleServer("TestServer", "/path/to/server")

    Bus().trigger(Events["SERVER.START"], server_name="TestServer")
