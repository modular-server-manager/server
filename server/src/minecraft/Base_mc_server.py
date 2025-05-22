from abc import ABC, abstractmethod

from gamuLogger import Logger

from ..bus import Bus, Events


class BaseMcServer(ABC):
    """
    Base class for Minecraft servers.
    This class is used to define the basic structure and functionality of a Minecraft server.
    """

    available_callbacks = {
        "on_server_start": "SERVER.START",
        "on_server_stop": "SERVER.STOP",
        "on_server_restart": "SERVER.RESTART",
        "on_console_send_message": "CONSOLE.SEND_MESSAGE",
        "on_console_send_command": "CONSOLE.SEND_COMMAND",
        "on_player_kick": "PLAYER.KICK",
        "on_player_ban": "PLAYER.BAN",
        "on_player_pardon": "PLAYER.PARDON",
        "on_player_list": "PLAYER.LIST",
    }

    def __init__(self, config_path: str):
        self.__bus = Bus()
        self.__register_callbacks()


    def __register_callbacks(self):
        for callback_name, event_name in self.available_callbacks.items():
            if hasattr(self, callback_name):
                event = Events[event_name]
                self.__bus.register(event, getattr(self, callback_name))
            else:
                Logger.warning(f"Callback {callback_name} not found in {self.__class__.__name__}. Skipping registration.")
                continue


if __name__ == "__main__":
    # example usage
    class ExampleServer(BaseMcServer):
        def on_server_start(self, timestamp: int, server_name: str):
            if server_name == "example_server":
                #start the server
                print(f"Server started at {timestamp}")

        ...
