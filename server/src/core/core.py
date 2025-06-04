import multiprocessing as mp
import os
import threading as th
import time
from datetime import datetime
from typing import Any, Dict, List

from config import JSONConfig
from gamuLogger import Logger
from version import Version

from ..bus import Bus, BusDispatcher, Events
from ..minecraft import McInstallersModules, McServersModules, WebInterface
from ..user_interface import UserInterfaceModules

Logger.set_module("Core")

class Core:
    def __init__(self, config_file: str):
        Logger.info("Initializing Core")
        self.__config = JSONConfig(config_file)

        # Initialize the bus dispatcher (will run in a separate thread)
        self.__bus_dispatcher = BusDispatcher(
            self.__config.get("bus.memory_size", default=8, set_if_not_found=True),
            self.__config.get("bus.max_string_length", default=256, set_if_not_found=True)
        )
        self.__bus_dispatcher_thread = th.Thread(
            target=self.__bus_dispatcher.mainloop,
            daemon=True,
            name="BusDispatcherThread"
        )

        # Initialize the bus to communicate with modules through the dispatcher
        bus_data = self.__bus_dispatcher.get_bus_data("core")
        self.__bus = Bus(
            bus_data
        )
        self._srv_config = JSONConfig(self.__config.get("server_config_path"))

        self.__ui_processes: list[mp.Process] = []

        self.__register_event_handlers()

        Logger.info("Core initialized successfully.")

    def start(self):
        Logger.info("Starting Core...")
        self.__bus_dispatcher_thread.start()
        self.__bus.start()
        self.__start_user_interface()

    def stop(self):
        Logger.info("Stopping Core...")
        self.__bus.stop()
        self.__bus_dispatcher.stop()
        self.__bus_dispatcher_thread.join()
        self.__bus_dispatcher.release_all_shared_memories()
        Logger.info("Core stopped.")

    def mainloop(self):
        """
        Main loop of the core. This method will block until the core is stopped.
        It is responsible for handling events and processing messages from the bus.
        """
        Logger.info("Core main loop started.")
        try:
            while True:
                time.sleep(1)  # Sleep to reduce CPU usage
        except KeyboardInterrupt:
            print("\r", end="")  # Clear the line
            Logger.info("Core main loop interrupted by user.")
        except Exception as e:
            Logger.error(f"Core main loop encountered an error: {e}")
        finally:
            self.stop()
    Logger.info("Core main loop stopped.")

    def __start_user_interface(self):
        to_load : dict[str, dict[str, Any]] = self.__config.get("user_interface_modules")
        for module_type, config in to_load.items():
            if module_type not in UserInterfaceModules:
                Logger.warning(f"User interface module {module_type} unknown. Skipping.")
                continue
            if not config['enabled']:
                Logger.info(f"User interface module {config['name']} is disabled. Skipping.")
                continue

            bus_data  = self.__bus_dispatcher.get_bus_data(config['name'])
            module_conf = config.copy()
            module_conf.pop('enabled')  # Remove 'enabled' key from config
            module_conf.pop("name")  # Remove 'name' key
            module_conf["database_path"] = self.__config.get("client_database_path")
            try:
                def a():
                    module_class = UserInterfaceModules[module_type]
                    module_instance = module_class(
                        bus_data=bus_data,
                        **module_conf,
                    )
                    module_instance.start()

                p = mp.Process(
                    target=a,
                    name=f"{module_type}_process",
                    daemon=True
                )
                self.__ui_processes.append(p)
                p.start()
            except Exception as e:
                Logger.fatal(f"Failed to initialize user interface module {config['name']}: {e}")
                self.stop()  # Stop the core if a critical UI module fails to start
            else:
                Logger.info(f"User interface module {config['name']} started successfully.")

    def __register_event_handlers(self):
        """
        Registers event handlers for the core.
        This method is called after the bus is initialized.
        """
        self.__bus.register(Events['SERVER.START'], self.on_server_start)
        self.__bus.register(Events['SERVER.RESTART'], self.on_server_restart)
        self.__bus.register(Events['SERVER.CREATE'], self.on_server_create)
        self.__bus.register(Events['SERVER.DELETE'], self.on_server_delete)
        self.__bus.register(Events['SERVER.RENAME'], self.on_server_rename)
        self.__bus.register(Events['SERVER.LIST'], self.on_server_list)
        self.__bus.register(Events['SERVER.INFO'], self.on_server_info)
        self.__bus.register(Events['GET_VERSIONS.MINECRAFT'], self.on_get_version_minecraft)
        self.__bus.register(Events['GET_VERSIONS.FORGE'], self.on_get_version_forge)

    def __is_server_path_valid(self, server_path: str) -> bool:
        """
        Checks if the server path is valid.
        :param server_path: Path to the server directory
        :return: True if the path is valid, False otherwise
        """
        server_path = os.path.normpath(server_path)
        if not server_path:
            Logger.error("Server path cannot be empty.")
            return False
        if not isinstance(server_path, str):
            Logger.error("Server path must be a string.")
            return False

        # for mc_dir in self.__config.get("minecraft_servers_dirs"): # must be in one of these directories
        if not any(server_path.startswith(mc_dir) for mc_dir in self.__config.get("minecraft_servers_dirs", [])):
            Logger.error(f"Server path {server_path} is not in the allowed directories: {self.__config.get('minecraft_servers_dirs')}")
            return False

        return True

    def __is_server_online(self, server_name: str) -> bool:
        """
        Checks if the server is running.
        :param server_name: Name of the server to check
        :return: True if the server is running, False otherwise
        """
        if server_name not in self._srv_config:
            Logger.error(f"Server {server_name} not found.")
            return False

        pinged = self.__bus.trigger(
            Events['SERVER.PING'],
            server_name=server_name,
            timeout=0.5 # if the server does not respond within 1 second, consider it offline
        )
        return pinged is True

    def __start_server(self, server_name : str, server_type: str, server_path: str):
        """
        Starts the specified server.
        :param server_name: The name of the server to start.
        :return: True if the server was started successfully, False otherwise.
        """
        Server = McServersModules[server_type]
        bus_data = self.__bus_dispatcher.get_bus_data(server_name)
        srv = Server(server_name, server_path, bus_data)
        srv.start()

    def on_server_start(self, timestamp : int, server_name: str):
        """
        Starts the specified server.
        :param timestamp: The timestamp of the request.
        :param server_name: The name of the server to start.
        """
        if server_name not in self._srv_config:
            Logger.error(f"Server {server_name} not found.")
            return

        if self.__is_server_online(server_name):
            Logger.warning(f"Server {server_name} is already running.")
            return

        srv_info = self._srv_config[server_name]
        server_type = srv_info['type']
        server_path = srv_info['path']
        if not self.__is_server_path_valid(server_path):
            Logger.error(f"Server path {server_path} is not valid. Cannot start server {server_name}.")
            return
        if server_type not in McServersModules:
            Logger.error(f"Server type {server_type} is not recognized. Cannot start server {server_name}.")
            return
        self.__start_server(server_name, server_type, server_path)

        # Trigger an event that the server has started
        self.__bus.trigger(
            Events['SERVER.STARTED'],
            server_name=server_name
        )

    def on_server_restart(self, timestamp : int, server_name: str):
        if not self.__is_server_online(server_name):
            Logger.warning(f"Server {server_name} is not running. Cannot restart.")
            return
        Logger.info(f"Restarting server {server_name}...")
        self.__bus.trigger( # Will wait for the server to stop
            Events['SERVER.STOP'],
            server_name=server_name
        )
        if self.__is_server_online(server_name):
            Logger.error(f"Server {server_name} did not stop properly. Cannot restart.")
            return
        Logger.info(f"Server {server_name} stopped successfully. Starting it again...")
        srv_info = self._srv_config[server_name]
        server_type = srv_info['type']
        server_path = srv_info['path']
        if not self.__is_server_path_valid(server_path):
            Logger.error(f"Server path {server_path} is not valid. Cannot restart server {server_name}.")
            return
        if server_type not in McServersModules:
            Logger.error(f"Server type {server_type} is not recognized. Cannot restart server {server_name}.")
            return
        self.__start_server(server_name, server_type, server_path)

    def on_server_create(self,
        timestamp : int,
        server_name: str,
        server_type: str,
        server_path: str,
        autostart: bool,
        mc_version : Version,
        framework_version: Version,
        ram: int,
    ) -> bool:
        mc_versions : Dict[Version, str] = WebInterface.get_mc_versions()
        if mc_version not in mc_versions:
            Logger.error(f"Invalid Minecraft version: {mc_version}. Available versions: {list(mc_versions.keys())}")
            return False
        url = mc_versions[mc_version]
        if server_type not in McInstallersModules:
            Logger.error(f"Unknown server type: {server_type}. Available types: {list(McInstallersModules.keys())}")
            return False
        if server_name in self._srv_config:
            Logger.error(f"Server with name {server_name} already exists.")
            return False
        if not self.__is_server_path_valid(server_path):
            Logger.error(f"Invalid server path: {server_path}. Must be in one of the allowed directories.")
            return False
        if not os.path.exists(server_path):
            try:
                os.makedirs(server_path, exist_ok=True)
            except Exception as e:
                Logger.error(f"Failed to create server directory {server_path}: {e}")
                return False
        if not isinstance(ram, int) or ram <= 0:
            Logger.error(f"Invalid RAM value: {ram}. Must be a positive integer.")
            return False

        try:
            McInstallersModules[server_type](
                installer_url=url,
                installation_dir=server_path,
            )
        except Exception as e:
            Logger.error(f"Failed to install server {server_name} of type {server_type}: {e}")
            return False
        else:
            self._srv_config.set(server_name, {
                "type": server_type,
                "path": server_path,
                "created_at": datetime.now().isoformat(),
                "autostart": autostart,
                "mc_version": str(mc_version),
                "framework_version": str(framework_version),
                "ram": ram,
            })

            self.__bus.trigger(
                Events['SERVER.CREATED'],
                server_name=server_name,
                server_type=server_type,
                server_path=server_path,
                autostart=autostart,
                mc_version=mc_version,
                framework_version=framework_version,
                ram=ram,
            )

            Logger.info(f"Server {server_name} created successfully.")
            return True

    def on_server_delete(self, timestamp : int, server_name: str):
        """
        Deletes a server.
        :param timestamp: The timestamp of the request.
        :param server_name: The name of the server to delete.
        :return: True if the server was deleted successfully, False otherwise.
        """
        if server_name not in self._srv_config:
            Logger.error(f"Server {server_name} not found.")
            return

        if self.__is_server_online(server_name):
            Logger.error(f"Server {server_name} is currently running. Please stop it before deleting.")
            return

        srv_info = self._srv_config[server_name]
        server_path = srv_info['path']
        try:
            if os.path.exists(server_path):
                os.rmdir(server_path)  # Remove the server directory
        except Exception as e:
            Logger.error(f"Failed to delete server directory {server_path}: {e}")
            return
        self._srv_config.remove(server_name)
        self.__bus.trigger(
            Events['SERVER.DELETED'],
            server_name=server_name,
        )
        Logger.info(f"Server {server_name} deleted successfully.")


    def on_server_rename(self, timestamp : int, server_name: str, new_name: str):
        """
        Renames a server.
        :param timestamp: The timestamp of the request.
        :param server_name: The current name of the server.
        :param new_name: The new name for the server.
        :return: True if the server was renamed successfully, False otherwise.
        """
        if server_name not in self._srv_config:
            Logger.error(f"Server {server_name} not found.")
            return
        if new_name in self._srv_config:
            Logger.error(f"Server with name {new_name} already exists.")
            return

        srv_info = self._srv_config[server_name]
        self._srv_config.set(new_name, srv_info)
        self._srv_config.remove(server_name)

        self.__bus.trigger(
            Events['SERVER.RENAMED'],
            server_name=server_name,
            new_name=new_name,
        )

        Logger.info(f"Server {server_name} renamed to {new_name}.")

    def on_server_list(self, timestamp : int) -> List[Dict[str, Any]]:
        """
        Returns a list of all servers managed by the core.
        Each server is represented as a dictionary with its properties.
        """
        result = []
        result.extend(
            {
                "name": name,
                "type": srv['type'],
                "mc_version": srv['mc_version'],
                "framework_version": srv['framework_version'],
                "online": self.__is_server_online(name)
            }
            for name, srv in self._srv_config._config.items()
        )
        return result

    def on_server_info(self, timestamp : int, server_name: str) -> Dict[str, Any]:
        """
        Returns detailed information about a specific server.
        """
        if server_name not in self._srv_config:
            Logger.error(f"Server {server_name} not found.")
            return {}

        srv_info = self._srv_config[server_name]
        return { # explicitly specify which fields to return to avoid exposing internal structure
            "name": server_name,
            "type": srv_info['type'],
            "path": srv_info['path'],
            "autostart": srv_info['autostart'],
            "mc_version": Version.from_string(srv_info['mc_version']),
            "framework_version": Version.from_string(srv_info['framework_version']),
            "ram": srv_info['ram'],
        }

    def on_get_version_minecraft(self, timestamp: int) -> list[Version]:
        """
        Returns the Minecraft version of the specified server.
        """
        return WebInterface.get_mc_versions().keys()

    def on_get_version_forge(self, timestamp: int, mc_version: Version) -> dict[Version, dict[str, Any]]:
        """
        Returns the Forge versions available for the specified Minecraft version.
        :param mc_version: Minecraft version
        :return: Dictionary of Forge versions with their properties
        """
        return WebInterface.get_forge_versions(mc_version)
