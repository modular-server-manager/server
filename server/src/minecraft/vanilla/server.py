import atexit
import re
import subprocess
import threading as th
from datetime import timedelta
from typing import Callable

from cache import Cache
from gamuLogger import Logger

from ...database.types import ServerStatus  # same enum for consistency
from ..properties import Properties
from ..rcon import RCON

RE_LOG_TEXT = re.compile(r"^.*\[[0-9]{2}:[0-9]{2}:[0-9]{2}\] \[.*/([A-Z]+)\] \[.*/(.*)\]: (.*)$") # first match is a color code, second match is the text

Logger.set_module("minecraft.server manager")


class MinecraftServer:
    """
    Class to manage a Minecraft server.
    """

    def __init__(self,
                 installation_dir: str,
                 on_chat_message : Callable[[str], None]|None = None,
                 on_stop : Callable[[], None]|None = None,
                ) -> None:
        self.name = installation_dir.split("/")[-1]
        self.installation_dir = installation_dir
        self.properties = Properties()
        self.properties.load(f"{self.installation_dir}/server.properties")
        self.__rcon = RCON("localhost", int(self.properties['rcon.port']), str(self.properties['rcon.password']))
        self.__ServerStatus = ServerStatus.STOPPED
        self.__server_thread = th.Thread(target=self.__start_server, daemon=True,  name=self.name)
        self.__on_chat_message = on_chat_message
        self.__on_stop = on_stop

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

    def __start_server(self):
        """
        Start the Minecraft Forge server./
        """
        Logger.set_module(f"minecraft.{self.name}")
        process = subprocess.Popen(
            ["./run.sh", "--nogui"],
            cwd=self.installation_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        self.__ServerStatus = ServerStatus.STARTING
        for line in iter(process.stdout.readline, b''):
            if self.__ServerStatus in [ServerStatus.STOPPING, ServerStatus.STOPPED]:
                break
            decoded_line = line.decode('utf-8').strip()
            if "Done" in decoded_line:
                self.__ServerStatus = ServerStatus.RUNNING
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
                if match.group(2) == "MinecraftServer" and match.group(1) == "INFO" and self.__on_chat_message:
                    self.__on_chat_message(match.group(3))
            if "Failed to start" in decoded_line:
                self.__ServerStatus = ServerStatus.ERROR
                break
        Logger.debug(f"waiting for server {self.name} to stop")
        process.stdout.close()
        process.wait()
        if self.__rcon:
            self.__rcon.close()
        Logger.debug(f"server {self.name} stopped")
        self.__ServerStatus = ServerStatus.STOPPED
        if self.__on_stop:
            self.__on_stop()

    def start(self):
        """
        Start the Minecraft Forge server.
        """
        Logger.info(f"Starting server \"{self.name}\"...")
        # Start the server with run.sh script in the installation directory
        self.__server_thread.start()

        while self.__ServerStatus not in (ServerStatus.RUNNING, ServerStatus.ERROR):
            th.Event().wait(0.2)

        if self.__ServerStatus == ServerStatus.ERROR:
            Logger.error(f"Server \"{self.name}\" failed to start.")
            return

        self.__rcon.open()
        self.__rcon.authenticate()
        Logger.info(
            f"Server \"{self.name}\" started"
        )

        atexit.register(self.__ensure_stop)

    def stop(self):
        """
        Stop the Minecraft Forge server.
        """
        self.send_command("stop")

    def __ensure_stop(self):
        """
        Ensure that the server is stopped when the script exits.
        """
        if self.__ServerStatus not in [ServerStatus.STOPPED, ServerStatus.STOPPING]:
            Logger.warning(f"Server {self.name} is not stopped. Stopping server...")
            self.stop()

    def send_command(self, command: str):
        """
        Send a command to the server.
        """
        Logger.debug(f"Sending command to server: {command}")
        if self.__rcon:
            return self.__rcon.send_command(command)
        Logger.warning("RCON connection not established. Cannot send command.")
        return None

    def reload_world(self):
        """
        Reload the world on the server.
        """
        return self.send_command("reload")

    def get_status(self):
        """
        Get the status of the server.
        """
        return self.__ServerStatus



    @Cache(expire_in=timedelta(seconds=2))
    def get_player_list(self):
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

    @Cache(expire_in=timedelta(hours=1))
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
