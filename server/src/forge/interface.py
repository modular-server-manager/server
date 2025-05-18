import atexit
import re
import subprocess
import threading as th
from enum import Enum
from typing import Callable

from gamuLogger import Logger
from properties import Properties
from rcon import RCON

# [20:37:10] [Server thread/INFO] [minecraft/DedicatedServer]: Starting minecraft server version 1.20.1
RE_LOG_TEXT = re.compile(r"^.*\[[0-9]{2}:[0-9]{2}:[0-9]{2}\] \[.*/([A-Z]+)\] \[.*/(.*)\]: (.*)$") # first match is a color code, second match is the text

Logger.set_module("forge server.server manager")


class State(Enum):
    """
    Enum to represent the state of the server.
    """
    STARTING = 1
    RUNNING  = 2
    STOPPING = 3
    STOPPED  = 4


class ForgeServer:
    """
    Class to manage a Minecraft Forge server.
    """

    def __init__(self, installation_dir: str, on_chat_message : Callable[[str], None]|None = None) -> None:
        self.name = installation_dir.split("/")[-1]
        self.installation_dir = installation_dir
        self.properties = Properties()
        self.properties.load(f"{self.installation_dir}/server.properties")
        self.__rcon = RCON("localhost", int(self.properties['rcon.port']), str(self.properties['rcon.password']))
        self.__state = State.STOPPED
        self.__server_thread = th.Thread(target=self.__start_server, daemon=True,  name=self.name)
        self.__on_chat_message = on_chat_message

    def set_on_chat_message(self, on_chat_message: Callable[[str], None]) -> None:
        """
        Set the callback function to be called when a chat message is received.
        """
        self.__on_chat_message = on_chat_message

    def __start_server(self):
        """
        Start the Minecraft Forge server./
        """
        Logger.set_module(f"forge server.{self.name}")
        process = subprocess.Popen(
            ["./run.sh", "--nogui"],
            cwd=self.installation_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        self.__state = State.STARTING
        for line in iter(process.stdout.readline, b''):
            if self.__state in [State.STOPPING, State.STOPPED]:
                break
            decoded_line = line.decode('utf-8').strip()
            if "Done" in decoded_line:
                self.__state = State.RUNNING
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
        process.stdout.close()
        process.wait()
        self.__state = State.STOPPED

    def start(self):
        """
        Start the Minecraft Forge server.
        """
        Logger.info(f"Starting server \"{self.name}\"...")
        # Start the server with run.sh script in the installation directory
        self.__server_thread.start()

        while self.__state != State.RUNNING:
            th.Event().wait(0.2)

        self.__rcon.open()
        self.__rcon.authenticate()
        Logger.info(
            f"Server \"{self.name}\" started"
        )

    def stop(self):
        """
        Stop the Minecraft Forge server.
        """
        if self.__state in [State.STOPPED, State.STOPPING]:
            Logger.warning(f"Server \"{self.name}\" is already stopped or stopping.")
            return
        self.__state = State.STOPPING
        if self.__rcon:
            self.__rcon.send_command("stop")
            self.__rcon.close()
            Logger.info(f"Stopping server \"{self.name}\"...")
        else:
            Logger.warning("RCON connection not established. Cannot stop the server.")
        self.__server_thread.join()
        Logger.info(f"Server \"{self.name}\" stopped")

    def ensure_stop(self):
        """
        Ensure that the server is stopped when the script exits.
        """
        if self.__state not in [State.STOPPED, State.STOPPING]:
            Logger.warning("Server is not stopped. Stopping server...")
            self.stop()

    def get_player_list(self):
        """
        Get the list of players currently online on the server.
        """
        if self.__rcon:
            if response := self.__rcon.send_command("list").strip():
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
        Logger.warning("RCON connection not established. Cannot get player list.")
        return None

    def reload_world(self):
        """
        Reload the world on the server.
        """
        if self.__rcon:
            return self.__rcon.send_command("reload")
        Logger.warning("RCON connection not established. Cannot reload world.")
        return None

    def send_command(self, command: str):
        """
        Send a command to the server.
        """
        Logger.debug(f"Sending command to server: {command}")
        if self.__rcon:
            return self.__rcon.send_command(command)
        Logger.warning("RCON connection not established. Cannot send command.")
        return None



if __name__ == "__main__":
    from gamuLogger import Levels
    Logger.set_default_module_level(Levels.TRACE)
    Logger.set_module_level("forge.properties", Levels.INFO)
    Logger.set_level("stdout", Levels.TRACE)

    from debug_tk import DebugTk

    server = ForgeServer("/var/minecraft/test")

    class SendCmd:
        def __init__(self):
            self.send = server.send_command
            self.write_res = None

        def __call__(self, cmd: str):
            if res := self.send(cmd):
                self.write_res(res)

    send_cmd = SendCmd()

    root = DebugTk()
    write_term, clear_term = root.add_terminal(send_cmd)
    send_cmd.write_res = write_term

    def stop():
        server.stop()
        root.close()

    root.add_button("Stop Server", stop)
    root.add_button("Reload World", server.reload_world)
    root.add_button("Get Player List", lambda: print(server.get_player_list()))

    server.start()
    atexit.register(server.ensure_stop)

    server.set_on_chat_message(write_term)

    root.mainloop()
