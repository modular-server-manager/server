import multiprocessing as mp
import os
import threading as th
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List
import shutil

from config import JSONConfig
from gamuLogger import Logger
from version import Version

from ..bus import Bus, BusDispatcher, Events
from ..utils.misc import gen_id
from ..minecraft import (McInstallersModules, McServersModules, McInstallersUrls,
                         BaseMcServer, ServerStatus, WebInterface)
from ..user_interface import BaseInterface, UserInterfaceModules

Logger.set_module("Core.Core")

class Core:
    def __init__(self, config_file: str):
        Logger.info("Initializing Core")
        self.__config = JSONConfig(config_file)
        self.__running = False

        # Initialize the bus dispatcher (will run in a separate thread)
        
        mem_size = self.__config.get("bus.memory_size", default=8, set_if_not_found=True)
        max_str_len = self.__config.get("bus.max_string_length", default=8192, set_if_not_found=True) # default of 8KB  
        
        if not isinstance(mem_size, int) or mem_size <= 0:
            Logger.error(f"Invalid bus memory size: {mem_size}. Must be a positive integer. Using default of 8MB.")
            raise ValueError("Invalid bus memory size in configuration.")
        if not isinstance(max_str_len, int) or max_str_len <= 0:
            Logger.error(f"Invalid bus max string length: {max_str_len}. Must be a positive integer. Using default of 8192 bytes.")
            raise ValueError("Invalid bus max string length in configuration.")
        
        self.__bus_dispatcher = BusDispatcher( mem_size, max_str_len)
        self.__bus_dispatcher_thread = th.Thread(
            target=self.__bus_dispatcher.mainloop,
            daemon=True,
            name="BusDispatcherThread"
        )

        # Initialize the bus to communicate with modules through the dispatcher
        bus_data = self.__bus_dispatcher.get_bus_data("core")
        self.__bus = Bus(bus_data)
        if self.__config.get("server_config_path", "", True) == "":
            raise ValueError("Server configuration path (server_config_path) is not set in the configuration file.")
        self._srv_config = JSONConfig(str(self.__config.get("server_config_path")))

        self.__ui_processes: Dict[str, mp.Process] = {}
        self.__mc_servers  : Dict[str, mp.Process] = {}

        self.__register_event_handlers()

        Logger.info("Core initialized successfully.")

    def start(self):
        self.__running = True
        Logger.info("Starting Core...")
        self.__bus_dispatcher_thread.start()
        self.__bus.start()
        self.__start_user_interfaces()
        self.__start_mc_servers()

    def stop(self):
        if not self.__running:
            Logger.warning("Core is already stopped.")
            return
        self.__running = False
        Logger.info("Stopping Core...")
        self.__bus.stop()
        self.__bus_dispatcher.stop()
        self.__bus_dispatcher_thread.join()
        self.__stop_user_interfaces()
        self.__stop_mc_servers()
        self.__bus_dispatcher.release_all_shared_memories()
        Logger.info("Core stopped.")

    def mainloop(self):
        """
        Main loop of the core. This method will block until the core is stopped.
        It is responsible for handling events and processing messages from the bus.
        """
        if not self.__running:
            return
        Logger.info("Core main loop started. Press Ctrl+C to stop the core.")
        try:
            while self.__running:
                time.sleep(1)  # Sleep to reduce CPU usage
        except KeyboardInterrupt:
            print("\r", end="")  # Clear the line
            Logger.info("Core main loop interrupted by user.")
        except Exception as e:
            Logger.error(f"Core main loop encountered an error: {e}")
            Logger.debug(traceback.format_exc())
        finally:
            if self.__running:
                self.stop()
        Logger.info("Core main loop stopped.")



    def __start_user_interfaces(self):
        """
        Initializes and start user interface modules based on the configuration.
        This method is called when the core is started.
        """
        if self.__config.get("user_interface_modules", {}, True) == {}:
            Logger.warning("No user interface modules configured.")
            return
        to_load : dict[str, dict[str, Any]] = self.__config.get("user_interface_modules") #type: ignore
        for module_type, config in to_load.items():
            Logger.info(f"Initializing user interface module {config['name']} of type {module_type}...")
            if module_type not in UserInterfaceModules:
                Logger.warning(f"User interface module {module_type} unknown. Skipping.")
                continue
            if not config['enabled']:
                Logger.info(f"User interface module {config['name']} is disabled. Skipping.")
                continue

            bus_data  = self.__bus_dispatcher.get_bus_data(module_type)
            module_conf = config.copy()
            module_conf.pop('enabled')  # Remove 'enabled' key from config
            module_conf.pop("name")  # Remove 'name' key
            module_conf["database_path"] = self.__config.get("client_database_path")
            try:
                module_class = UserInterfaceModules[module_type]
                def __start_ui_module():
                    module_instance = module_class(bus_data=bus_data, **module_conf)
                    module_instance.start()

                p = mp.Process(
                    target=__start_ui_module,
                    name=f"{module_type}",
                    daemon=True
                )
                Logger.info(f"Starting user interface module {config['name']}...")
                p.start()  # Start the process
                self.__ui_processes[config['name']] = p  # Store the process
            except Exception as e:
                Logger.fatal(f"Failed to initialize user interface module {config['name']}: {e}")
                Logger.debug(traceback.format_exc())
                self.stop()  # Stop the core if a critical UI module fails to start
            else:
                Logger.info(f"User interface module {config['name']} initiated and started successfully.")

    # def __start_user_interfaces(self):
    #     """
    #     Starts all user interface modules.
    #     This method is called when the core is started.
    #     """
    #     Logger.info("Starting user interface modules...")
    #     self.__init_user_interfaces()
    #     for ui_name, ui_process in self.__ui_processes.items():
    #         if not ui_process.is_alive():
    #             Logger.info(f"Starting user interface process {ui_name}...")
    #             ui_process.start()
    #             Logger.info(f"User interface process {ui_name} started with PID {ui_process.pid}.")
    #         else:
    #             Logger.warning(f"User interface process {ui_name} is already running with PID {ui_process.pid}.")

    def __stop_user_interfaces(self):
        """
        Stops all user interface modules.
        This method is called when the core is stopped.
        """
        Logger.info("Stopping user interface modules...")
        for ui_name, ui_process in self.__ui_processes.items():
            if ui_process.is_alive():
                Logger.info(f"Stopping user interface process {ui_name} with PID {ui_process.pid}...")
                ui_process.join(timeout=30)  # Wait for the process to finish
                if ui_process.is_alive():
                    Logger.warning(f"User interface process {ui_name} did not stop gracefully. Terminating...")
                    ui_process.terminate()
                    ui_process.join()
                Logger.info(f"User interface process {ui_name} stopped successfully.")


    def __start_server(self, server_name: str):
        """
        Starts the specified server.
        :param server_name: Name of the server to start
        """
        Logger.info(f"Initializing server {server_name}...")
        try:
            server_type = self._srv_config.get(f"{server_name}.type")
            server_path = self._srv_config.get(f"{server_name}.path")
            
            if not isinstance(server_type, str) or server_type not in McServersModules:
                Logger.error(f"Invalid or unknown server type for server {server_name}. Cannot start server.")
                return
            if not isinstance(server_path, str) or not os.path.exists(server_path):
                Logger.error(f"Invalid or non-existent server path for server {server_name}. Cannot start server.")
                return

            Server = McServersModules[server_type]
            bus_data = self.__bus_dispatcher.get_bus_data(server_name)
            ram = self._srv_config.get(f"{server_name}.ram", default=1024, set_if_not_found=True)
            if not isinstance(ram, int) or ram <= 0:
                Logger.error(f"Invalid RAM value for server {server_name}. Cannot start server.")
                return
            mc_version_raw = self._srv_config.get(f"{server_name}.mc_version")
            if not isinstance(mc_version_raw, str):
                Logger.error(f"Invalid Minecraft version for server {server_name}. Cannot start server.")
                return
            mc_version = Version.from_string(mc_version_raw)
            
            def __start_mc_server():
                srv = Server(server_name, server_path, ram, mc_version, bus_data)
                srv.start()
            p = mp.Process(
                target=__start_mc_server,
                name=f"Server_{server_name}",
                daemon=True
            )
            Logger.info(f"Starting Minecraft server {server_name} of type {server_type} at {server_path} with RAM {ram}MB...")
            p.start()  # Start the process
            self.__mc_servers[server_name] = p  # Store the process
        except Exception as e:
            Logger.error(f"Failed to init server {server_name}: {e}")
            Logger.debug(traceback.format_exc())

    def __stop_server(self, server_name: str):
        srv_process = self.__mc_servers[server_name]
        if srv_process.is_alive():
            Logger.info(f"Stopping Minecraft server {server_name} with PID {srv_process.pid}...")
            self.__bus.trigger(
                Events['SERVER.STOP'],
                server_name=server_name,
                timeout=30  # Wait for 30 seconds for the server to stop
            )
            srv_process.join(timeout=30)
            if srv_process.is_alive():
                Logger.warning(f"Minecraft server {server_name} did not stop gracefully. Terminating...")
                srv_process.terminate()
                srv_process.join()
            Logger.info(f"Minecraft server {server_name} stopped successfully.")

    def __restart_server(self, server_name: str):
        """
        Restarts the specified server.
        :param server_name: Name of the server to restart
        """
        Logger.info(f"Restarting server {server_name}...")
        self.__stop_server(server_name)
        self.__start_server(server_name)

    def __start_mc_servers(self):
        """
        Initializes Minecraft servers based on the configuration.
        This method is called when the core is started.
        """
        Logger.info("Initializing Minecraft servers...")
        for server_name, srv_info in self._srv_config.items():
            if srv_info.get("autostart", False):
                self.__start_server(server_name)
            else:
                Logger.info(f"Server {server_name} is not set to autostart. Skipping.")

    def __stop_mc_servers(self):
        """
        Stops all Minecraft servers.
        This method is called when the core is stopped.
        """
        Logger.info("Stopping Minecraft servers...")
        for srv_name in self.__mc_servers.keys():
            self.__stop_server(srv_name)



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
        self.__bus.register(Events['GET_DIRECTORIES.MINECRAFT'], self.on_get_minecraft_directories)

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

        allowed_dirs = self.__get_mc_dirs()

        # for mc_dir in self.__config.get("minecraft_servers_dirs"): # must be in one of these directories
        if not any(server_path.startswith(mc_dir) for mc_dir in allowed_dirs):
            Logger.error(f"Server path {server_path} is not in the allowed directories: {allowed_dirs}")
            return False

        return True

    def __get_server_status(self, server_name: str) -> ServerStatus:
        """
        Checks if the server is running.
        :param server_name: Name of the server to check
        :return: True if the server is running, False otherwise
        """
        if server_name not in self._srv_config:
            Logger.error(f"Server {server_name} not found.")
            return ServerStatus.STOPPED

        pinged : str = self.__bus.trigger(
            Events['SERVER.PING'],
            server_name=server_name,
            timeout=0.5 # if the server does not respond within 0.5 second, consider it offline
        )
        return ServerStatus.from_string(pinged) if pinged else ServerStatus.STOPPED

    def __get_mc_dirs(self) -> List[str]:
        try:
            data = []
            Logger.trace("Fetching Minecraft server directories from configuration.")
            for i in range(len(self.__config.get("minecraft_servers_dirs", []))): # type: ignore
                dir_path = self.__config.get(f"minecraft_servers_dirs.{i}")
                if not isinstance(dir_path, str):
                    Logger.warning(f"Invalid directory path at index {i}: {dir_path}. Skipping.")
                    continue
                data.append(os.path.normpath(dir_path))
            Logger.trace(f"Found Minecraft server directories: {data}")
            return data
        except Exception as e:
            Logger.error(f"Failed to get Minecraft directories: {e}")
            Logger.debug(traceback.format_exc())
            return []

    def on_server_start(self, timestamp : datetime, server_name: str):
        """
        Starts the specified server.
        :param timestamp: The timestamp of the request.
        :param server_name: The name of the server to start.
        """
        if server_name not in self._srv_config:
            Logger.error(f"Server {server_name} not found.")
            return

        if self.__get_server_status(server_name):
            Logger.warning(f"Server {server_name} is already running.")
            return


        self.__start_server(server_name)

        # Trigger an event that the server has started
        self.__bus.trigger(
            Events['SERVER.STARTED'],
            server_name=server_name
        )

    def on_server_restart(self, timestamp : datetime, server_name: str):
        if not self.__get_server_status(server_name):
            Logger.warning(f"Server {server_name} is not running. Cannot restart.")
            return
        Logger.info(f"Restarting server {server_name}...")
        self.__restart_server(server_name)

    def on_server_create(self,
        timestamp : datetime,
        server_name: str,
        server_type: str,
        server_path: str,
        autostart: bool,
        mc_version : Version,
        modloader_version: Version,
        ram: int,
    ) -> None:
        mc_versions : List[Version] = WebInterface.get_mc_versions()
        server_id = gen_id()
        
        # data validation
        if mc_version not in mc_versions:
            Logger.error(f"Invalid Minecraft version: {mc_version}. Available versions: {mc_versions}")
            return
        if server_type not in McInstallersModules:
            Logger.error(f"Unknown server type: {server_type}. Available types: {list(McInstallersModules.keys())}")
            return
        if server_name in self._srv_config:
            Logger.error(f"Server with name {server_name} already exists.")
            return
        if not self.__is_server_path_valid(server_path):
            Logger.error(f"Invalid server path: {server_path}. Must be in one of the allowed directories.")
            return
        if not isinstance(ram, int) or ram <= 0:
            Logger.error(f"Invalid RAM value: {ram}. Must be a positive integer.")
            return


        server_path = os.path.join(server_path, server_id)
        if os.path.exists(server_path):
            Logger.error(f"Server path {server_path} already exists.")
            return
        
        Logger.info(f"Creating server {server_name} of type {server_type} at {server_path}")
        self.__bus.trigger(
                Events['SERVER.CREATING'],
                server_name=server_name,
                server_type=server_type,
                server_path=server_path,
                autostart=autostart,
                mc_version=mc_version,
                modloader_version=modloader_version,
                ram=ram,
            )
        
        os.makedirs(server_path, exist_ok=True)
        
        try:
            url = McInstallersUrls[server_type](mc_version, modloader_version)
            McInstallersModules[server_type](
                url,
                server_path,
                mc_version
            )
        except Exception as e:
            Logger.error(f"Failed to install server {server_name} of type {server_type}: {e}")
            Logger.debug(traceback.format_exc())
            return
        else:
            self._srv_config.set(server_name, {
                "id": server_id,
                "type": server_type,
                "path": server_path,
                "created_at": datetime.now().isoformat(),
                "autostart": autostart,
                "mc_version": str(mc_version),
                "modloader_version": str(modloader_version),
                "ram": ram,
            })

            self.__bus.trigger(
                Events['SERVER.CREATED'],
                server_name=server_name,
                server_type=server_type,
                server_path=server_path,
                autostart=autostart,
                mc_version=mc_version,
                modloader_version=modloader_version,
                ram=ram,
            )

            Logger.info(f"Server {server_name} created successfully.")

    def on_server_delete(self, timestamp : datetime, server_name: str):
        """
        Deletes a server.
        :param timestamp: The timestamp of the request.
        :param server_name: The name of the server to delete.
        :return: True if the server was deleted successfully, False otherwise.
        """
        if server_name not in self._srv_config:
            Logger.error(f"Server {server_name} not found.")
            return

        if self.__get_server_status(server_name):
            Logger.error(f"Server {server_name} is currently running. Please stop it before deleting.")
            return

        srv_info = self._srv_config[server_name]
        server_path = srv_info['path']
        try:
            if os.path.exists(server_path):
                shutil.rmtree(server_path)  # Remove the server directory
        except Exception as e:
            Logger.error(f"Failed to delete server directory {server_path}: {e}")
            return
        self._srv_config.remove(server_name)
        self.__bus.trigger(
            Events['SERVER.DELETED'],
            server_name=server_name,
        )
        Logger.info(f"Server {server_name} deleted successfully.")

    def on_server_rename(self, timestamp : datetime, server_name: str, new_name: str):
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

    def on_server_list(self, timestamp : datetime) -> List[Dict[str, Any]]:
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
                "modloader_version": srv['modloader_version'],
                "status": self.__get_server_status(name).name,
            }
            for name, srv in self._srv_config._config.items()
        )
        return result

    def on_server_info(self, timestamp : datetime, server_name: str) -> Dict[str, Any]:
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
            "modloader_version": Version.from_string(srv_info['modloader_version']),
            "ram": srv_info['ram'],
            "started_at": self.__bus.trigger(
                Events['SERVER.STARTED_AT'],
                server_name=server_name,
                timeout=0.5  # Wait for 0.5 seconds for the server to respond
            ),
        }

    def on_get_version_minecraft(self, timestamp: datetime) -> list[Version]:
        """
        Returns the Minecraft version of the specified server.
        """
        try:
            return WebInterface.get_mc_versions()
        except Exception as e:
            Logger.error(f"Failed to fetch Minecraft versions: {e}")
            Logger.debug(traceback.format_exc())
            return []

    def on_get_version_forge(self, timestamp: datetime, mc_version: Version) -> dict[Version, dict[str, Any]]:
        """
        Returns the Forge versions available for the specified Minecraft version.
        :param mc_version: Minecraft version
        :return: Dictionary of Forge versions with their properties
        """
        try:
            return WebInterface.get_forge_versions(mc_version)
        except Exception as e:
            Logger.error(f"Failed to fetch Forge versions for Minecraft version {mc_version}: {e}")
            Logger.debug(traceback.format_exc())
            return {}

    def on_get_minecraft_directories(self, timestamp: datetime) -> list[str]:
        """
        Returns a list of all available Minecraft server directories.
        This is useful for the user interface to provide a selection of directories.
        """
        return self.__get_mc_dirs()
