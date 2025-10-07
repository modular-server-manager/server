from datetime import datetime, timedelta
from typing import Any, Dict
from traceback import format_exc

import argon2.exceptions
from gamuLogger import Logger
from version import Version

from ..bus import Bus, BusData, Callback, Event, Events
from ..utils.hash import hash_string, verify_hash
from ..utils.misc import time_from_now
from .database import AccessLevel, AccessToken, Database, User

Logger.set_module("User Interface.Base")

class BaseInterface:
    """
    Base interface for the user interface of the server.
    This interface provides methods for user management and Minecraft server management.
    It uses a bus to communicate with the server and a database to store user information.
    It also provides methods to trigger events and handle callbacks.
    The list of callbacks is defined in the `callback_map` dictionary, which maps method names to events.
    """
    callback_map: dict[str, Event] = {
        "on_server_starting": Events["SERVER.STARTING"],
        "on_server_started": Events["SERVER.STARTED"],
        "on_server_stopping": Events["SERVER.STOPPING"],
        "on_server_stopped": Events["SERVER.STOPPED"],
        "on_server_crashed": Events["SERVER.CRASHED"],
        "on_server_created": Events["SERVER.CREATED"],
        "on_server_deleted": Events["SERVER.DELETED"],
        "on_server_renamed": Events["SERVER.RENAMED"],
        "on_console_message_received": Events["CONSOLE.MESSAGE_RECEIVED"],
        "on_console_log_received": Events["CONSOLE.LOG_RECEIVED"],
        "on_player_joined": Events["PLAYERS.JOINED"],
        "on_player_left": Events["PLAYERS.LEFT"],
        "on_player_kicked": Events["PLAYERS.KICKED"],
        "on_player_banned": Events["PLAYERS.BANNED"],
        "on_player_pardoned": Events["PLAYERS.PARDONED"]
    }

    def __init__(self, bus_data : BusData, database_path: str):
        if hasattr(self, "_BaseInterface__bus"): # Avoid reinitializing the bus
            return
        self.__bus = Bus(bus_data)

        self._database = Database(database_path)

        self.__register_methods()

    def __register_methods(self):
        for method_name, event in self.callback_map.items():
            if hasattr(self, method_name):
                callback : Callback = getattr(self, method_name)
                if callable(callback):
                    self.__bus.register(event, callback)
                else:
                    Logger.warning(f"Method {method_name} is not callable. Skipping subscription.")
            else:
                Logger.trace(f"Method {method_name} not found in {self.__class__.__name__}. Skipping subscription.")

    def trigger(self, event_name: str, **kwargs):
        """
        Trigger an event with the given name and arguments.
        """
        if event_name in Events:
            event = Events[event_name]
            return self.__bus.trigger(event, **kwargs)
        Logger.trace("\n".join(repr(e) for e in Events))
        raise IndexError(f"Event {event_name} does not exist.")

    def start(self):
        """
        Start the interface.
        """
        Logger.info(f"Starting {self.__class__.__name__} interface.")
        try:
            self.__bus.start()
        except Exception as e:
            Logger.error(f"Error starting {self.__class__.__name__} interface: {e}")
            Logger.debug(format_exc())

    def stop(self):
        """
        Stop the interface and clean up resources.
        """
        Logger.info(f"Stopping {self.__class__.__name__} interface.")
        self.__bus.stop()
        Logger.info(f"{self.__class__.__name__} interface stopped.")


####################################### User database methods #####################################

    def login(self, username: str, password: str, remember : bool = False) -> AccessToken:
        """
        Login a user with the given username and password.
        If remember is True, the user will be remembered for future logins.
        Returns True if login is successful, False otherwise.
        """

        if not username or not password:
            Logger.trace(
                f"Missing parameters for login. got username: {username}, password: {password}, remember: {remember}"
            )
            raise ValueError("Missing parameters for login. Username and password are required.")

        if not self._database.has_user(username):
            raise ValueError(f"User {username} does not exist.")
        user = self._database.get_user(username)
        try:
            if not verify_hash(password, user.password):
                Logger.trace(f"User {username} provided invalid password")
                raise ValueError("Invalid password.")
        except argon2.exceptions.VerifyMismatchError as e:
            Logger.trace(f"Password verification failed for user {username}: {e}")

        token = AccessToken.new(username, time_from_now(timedelta(hours=1)), remember)
        self._database.set_user_token(token)
        self._database.update_user(User(
            username=user.username,
            password=user.password,
            access_level=user.access_level,
            registered_at=user.registered_at,
            last_login=datetime.now()
        ))
        Logger.trace(f"User {username} logged in with token {token.token}")
        return token

    def register(self, username: str, password: str, remember : bool = False) -> AccessToken:
        """
        Register a new user with the given username and password.
        Returns the created User object.
        """
        if not username or not password:
            Logger.debug(
                f"Missing parameters for register. got username: {username}, password: {password}, remember: {remember}"
            )
            raise ValueError("Missing parameters for registration. Username and password are required.")

        password = hash_string(password)

        if self._database.has_user(username):
            Logger.debug(f"User {username} already exists")
            raise ValueError(f"User {username} already exists.")

        self._database.add_user(User(
            username=username,
            password=password,
            access_level=AccessLevel.USER,
            registered_at=datetime.now(),
            last_login=datetime.now()
        ))
        token = AccessToken.new(username, time_from_now(timedelta(hours=1)), remember)
        self._database.set_user_token(token)
        Logger.debug(f"User {username} registered with token {token.token}")
        return token

    def logout(self, token: str):
        """
        Logout a user with the given token.
        """
        if not token:
            raise ValueError("Missing token for logout.")

        if not self._database.exist_user_token(token):
            raise ValueError(f"Token {token} does not exist.")

        self._database.delete_user_token(token)
        Logger.debug(f"User logged out with token {token}.")

    def delete_user(self, token : str):
        access_token = self._database.get_user_token_by_token(token)
        if not access_token or not access_token.is_valid():
            raise ValueError("Invalid or expired token.")

        user = self._database.get_user(access_token.username)
        if not user:
            raise ValueError(f"User {access_token.username} does not exist.")

        self._database.delete_user(user.username)
        self._database.delete_user_token(token)
        Logger.debug(f"User {user.username} deleted successfully.")

    def get_user_info(self, token: str) -> User:
        """
        Get user information by token.
        """
        if not token:
            raise ValueError("Missing token for get_user_info.")

        access_token = self._database.get_user_token_by_token(token)
        if not access_token or not access_token.is_valid():
            raise ValueError("Invalid or expired token.")

        if user := self._database.get_user(access_token.username):
            return user
        else:
            raise ValueError(f"User {access_token.username} does not exist.")

    def update_password(self, token: str, password: str):
        """
        Update the password for the user associated with the given token.
        """
        access_token = self._database.get_user_token_by_token(token)
        if not access_token or not access_token.is_valid():
            raise ValueError("Invalid or expired token.")

        user = self._database.get_user(access_token.username)

        if not password:
            raise ValueError("Missing password for update.")
        user.password = hash_string(password)
        self._database.update_user(user)
        Logger.debug(f"Password for user {user.username} updated successfully.")

    def get_user_info_by_username(self, username: str) -> User:
        """
        Get user information by username.
        """
        if not username:
            raise ValueError("Missing username for get_user_info_by_username.")

        if user := self._database.get_user(username):
            return user
        else:
            raise ValueError(f"User {username} does not exist.")

    def update_user_access(self, username: str, access_level: str):
        if not access_level:
            raise ValueError("Missing access level for update_user_access.")
        user = self._database.get_user(username)
        if not user:
            raise ValueError(f"User {username} does not exist.")
        user.access_level = AccessLevel[access_level]
        self._database.update_user(user)

    def update_user_password(self, username: str, password: str):
        """
        Update the password for the user with the given username.
        """
        if not password:
            raise ValueError("Missing password for update_user_password.")
        user = self._database.get_user(username)
        if not user:
            raise ValueError(f"User {username} does not exist.")
        user.password = hash_string(password)
        self._database.update_user(user)

 #################################### Minecraft server methods ####################################

    def list_mc_versions(self) -> list[Version]:
        """
        List all available Minecraft server versions.
        """
        versions : list[Version] = self.trigger("GET_VERSIONS.MINECRAFT")
        return versions

    def list_forge_versions(self, mc_version: Version) -> list[Version]:
        """
        List all available Forge versions for the given Minecraft version.
        """
        versions = self.trigger("GET_VERSIONS.FORGE", mc_version=mc_version)
        return versions

    def list_servers(self) -> list[Dict[str, Any]]:
        """
        List all Minecraft servers.
        """
        servers = self.trigger("SERVER.LIST")
        return servers or []

    def get_server_info(self, server_name: str) -> Dict[str, Any]:
        """
        Get information about a specific Minecraft server by its ID.
        """
        if server_info := self.trigger("SERVER.INFO", server_name=server_name):
            return server_info
        else:
            raise ValueError(f"Server with name {server_name} does not exist.")

    def create_server(self, /,
        name: str,
        type: str,
        path: str,
        autostart: bool,
        mc_version: Version,
        modloader_version: Version = None,
        ram: int = 1024,
    ) -> None:
        """
        Create a new Minecraft server with the given parameters.
        Returns the created server information.
        """
        if not name or not type or not path or not mc_version:
            raise ValueError("Missing parameters for create_server. Name, type, path, and Minecraft version are required.")

        if type != "vanilla" and modloader_version is None:
            raise ValueError("Missing modloader version for non-vanilla server types.")
        if not isinstance(ram, int) or ram <= 0:
            raise ValueError("RAM must be a positive integer.")

        if self.trigger("SERVER.CREATE",
                        server_name=name,
                        server_type=type,
                        server_path=path,
                        autostart=autostart,
                        mc_version=mc_version,
                        modloader_version=modloader_version or Version(0,0,0),
                        ram=ram):
            Logger.debug(f"Server {name} created successfully.")
        else:
            raise ValueError(f"Failed to create server {name}. It may already exist or there was an error in the parameters.")

    def list_mc_server_dirs(self) -> list[str]:
        """
        List all available Minecraft server directories.
        """
        return self.trigger("GET_DIRECTORIES.MINECRAFT") or []

    def start_server(self, server_name: str) -> None:
        """
        Start a Minecraft server by its name.
        """
        if not server_name:
            raise ValueError("Missing server name for start_server.")

        self.trigger("SERVER.START", server_name=server_name)
    
    def stop_server(self, server_name: str) -> None:
        """
        Stop a Minecraft server by its name.
        """
        if not server_name:
            raise ValueError("Missing server name for stop_server.")

        self.trigger("SERVER.STOP", server_name=server_name)
    
    def restart_server(self, server_name: str) -> None:
        """
        Restart a Minecraft server by its name.
        """
        if not server_name:
            raise ValueError("Missing server name for restart_server.")

        self.trigger("SERVER.RESTART", server_name=server_name)


