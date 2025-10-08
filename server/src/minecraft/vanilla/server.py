import re
import subprocess
import threading as th
from datetime import datetime, timedelta
from typing import Callable

from cache import Cache
from gamuLogger import Logger
from version import Version

from ...bus import BusData
from ..Base_mc_server import BaseMcServer, ServerStatus
from ..properties import Properties
from ..rcon import RCON

RE_LOG_TEXT = re.compile(r"^.*\[[0-9]{2}:[0-9]{2}:[0-9]{2}\] \[.*/([A-Z]+)\] \[.*/(.*)\]: (.*)$") # first match is a color code, second match is the text

Logger.set_module("Mc Server.Vanilla Server")


class MinecraftServer(BaseMcServer):
    """
    Class to manage a Minecraft server.
    """

    def __init__(self,
                 name : str,
                 path: str,
                 ram : int,
                 mc_version : Version,
                 bus_data : BusData
                ) -> None:
        super().__init__(name, path, ram=ram, mc_version=mc_version, bus_data=bus_data)
        self.properties = Properties()
        self.properties.load(f"{self.path}/server.properties")
        self.__rcon = RCON("localhost", int(self.properties['rcon.port']), str(self.properties['rcon.password']))
        self.__server_thread = th.Thread(target=self.__start_server, daemon=True,  name=self.name)
        self.__on_chat_message = None
        self.__on_stop = None

    def set_on_chat_message(self, on_chat_message: Callable[[str], None]) -> None:
        """
        Set the callback function to be called when a chat message is received.
        """
        self.__on_chat_message = on_chat_message

    def set_on_stop(self, on_stop: Callable[[], None]) -> None:
        """
        Set the callback function to be called when the server stops.
        """
        self.__on_stop = on_stop

    def _spawn_server_process(self) -> subprocess.Popen[bytes]:
        """
        Spawn the server process.
        """
        return subprocess.Popen(
            ["java", f"-Xmx{self._ram}M", "-jar", f"server-{self._mc_version}.jar", "--nogui"],
            cwd=self.path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    def __start_server(self):
        """
        Start the Minecraft Forge server./
        """
        Logger.set_module(f"Mc Server.{self.name}")

        process = self._spawn_server_process()

        self._ServerStatus = ServerStatus.STARTING
        if process.stdout is None:
            Logger.error("Failed to start server process: stdout is None")
            self._ServerStatus = ServerStatus.ERROR
            return

        for line in iter(process.stdout.readline, b''):
            if self._ServerStatus in [ServerStatus.STOPPING, ServerStatus.STOPPED]:
                break
            decoded_line = line.decode('utf-8').strip()
            if "Done" in decoded_line:
                self._ServerStatus = ServerStatus.RUNNING
            for l in decoded_line.split("\n"):
                match = RE_LOG_TEXT.match(l)
                if not match:
                    continue
                level = match.group(1)
                if level == "INFO":
                    Logger.info(match.group(3))
                elif level == "WARN":
                    Logger.warning(match.group(3))
                elif level == "ERROR":
                    Logger.error(match.group(3))
                elif level == "FATAL":
                    Logger.fatal(match.group(3))
                else:
                    Logger.debug(match.group(3))
                if match.group(2) == "MinecraftServer" and self.__on_chat_message:
                    self.__on_chat_message(match.group(3))
            if "Failed to start" in decoded_line:
                self._ServerStatus = ServerStatus.ERROR
                break
        Logger.debug(f"waiting for server {self.name} to stop")
        process.stdout.close()
        process.wait()
        if self.__rcon:
            self.__rcon.close()
        Logger.debug(f"server {self.name} stopped")
        self._ServerStatus = ServerStatus.STOPPED
        if self.__on_stop:
            self.__on_stop()

    def _start(self):
        self.__server_thread.start()

    def _after_start(self):
        self.__rcon.open()
        self.__rcon.authenticate()


    def _stop(self):
        self.send_command("stop")


    def send_command(self, command: str):
        """
        Send a command to the server.
        """
        Logger.debug(f"Sending command to server: {command}")
        if self.__rcon:
            return self.__rcon.send_command(command)
        Logger.warning("RCON connection not established. Cannot send command.")
        return ""

    def reload_world(self):
        """
        Reload the world on the server.
        """
        return self.send_command("reload")

    def get_status(self):
        """
        Get the status of the server.
        """
        return self._ServerStatus


    @Cache(expire_in=timedelta(seconds=2)) # type: ignore[reportArgumentType]
    def get_player_list(self) -> list[str]:
        """
        Get the list of players currently online on the server.
        """
        if response := self.send_command("list").strip():
            try:
                player_list = response.split(":")[1].split(",")
            except Exception as e:
                Logger.error(f"Error parsing player list: {e}")
                Logger.error(f"Response: '{response}'")
                return []
            return list(map(lambda x: x.strip(), player_list))
        else:
            Logger.warning("No players online.")
            return []

    @Cache(expire_in=timedelta(hours=1)) # type: ignore[reportArgumentType]
    def get_seed(self) -> str:
        """
        Get the seed of the world on the server.
        """
        if response := self.send_command("seed"):
            try:
                seed = response.split(":")[1].strip()
                if seed.startswith("[") and seed.endswith("]"):
                    seed = seed[1:-1]
                seed = seed.strip()
                if not seed.isdigit():
                    raise ValueError(f"Seed is not a number: {seed}")
            except Exception as e:
                Logger.error(f"Error parsing seed: {e}")
                Logger.error(f"Response: '{response}'")
                return ""
            return seed
        else:
            Logger.warning("No seed found.")
            return ""


    def on_server_stop(self, timestamp: datetime, server_name: str) -> bool|None:
        if server_name == self.name:
            Logger.info(f"Server {self.name} received stop signal at {timestamp}.")
            self.stop()
            return True
        return None

    def on_server_seed(self, timestamp: datetime, server_name: str) -> str|None:
        if server_name == self.name:
            Logger.info(f"Server {self.name} received seed request at {timestamp}.")
            return self.get_seed()
        return None

    def on_console_send_message(self, timestamp: datetime, server_name: str, _from : str, message: str) -> None:
        if server_name == self.name:
            Logger.info(f"Server {self.name} received console message at {timestamp}: {message} from {_from}")
            cmd = 'tellraw @a {"text": "<{_from}> {message}", "color": "white"}'
            self.send_command(cmd.format(_from=_from, message=message))

    def on_console_send_command(self, timestamp: datetime, server_name: str, command: str) -> None:
        if server_name == self.name:
            Logger.info(f"Server {self.name} received console command at {timestamp}: {command}")
            self.send_command(command)

    def on_player_kick(self, timestamp: datetime, server_name: str, player_name: str, reason: str) -> None:
        if server_name == self.name:
            Logger.info(f"Server {self.name} received kick request for player {player_name} at {timestamp}: {reason}")
            self.send_command(f"kick {player_name} {reason}")

    def on_player_ban(self, timestamp: datetime, server_name: str, player_name: str, reason: str) -> None:
        if server_name == self.name:
            Logger.info(f"Server {self.name} received ban request for player {player_name} at {timestamp}: {reason}")
            self.send_command(f"ban {player_name} {reason}")

    def on_player_pardon(self, timestamp: datetime, server_name: str, player_name: str) -> None:
        if server_name == self.name:
            Logger.info(f"Server {self.name} received pardon request for player {player_name} at {timestamp}.")
            self.send_command(f"pardon {player_name}")

    def on_player_list(self, timestamp: datetime, server_name: str) -> list[str]|None:
        if server_name == self.name:
            Logger.info(f"Server {self.name} received player list request at {timestamp}.")
            return self.get_player_list()
        return None
