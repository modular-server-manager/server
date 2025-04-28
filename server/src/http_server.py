from flask import Flask, request
import pathlib
import os
from gamuLogger import Logger
from mimetypes import guess_type
import traceback

from .forge_web_interface import WebInterface
from .version import Version
from .config import JSONConfig
from .http_code import HttpCode as HTTP
from . import installer

Logger.set_module("server")

BASE_PATH = __file__[:__file__.rfind('/')] # get the base path of the server

STATIC_PATH = f'{BASE_PATH}/client'


class HttpServer:
    def __init__(self, port: int = 5000):
        self.config = JSONConfig(f"{BASE_PATH}/config.json")
        self._port = port
        self.__app = Flask(__name__)

        self.__config_api_route()
        self.__config_static_route()

    def __config_static_route(self):
        @self.__app.route('/')
        def index():
            return static_proxy('index.html')
            

        @self.__app.route('/<path:path>')
        def static_proxy(path):
            try:
                # send the file to the browser
                Logger.trace(f"requesting {STATIC_PATH}/{path}")
                if not os.path.exists(f"{STATIC_PATH}/{path}"):
                    Logger.trace(f"File not found: {STATIC_PATH}/{path}")
                    return "File not found", HTTP.NOT_FOUND
                content = pathlib.Path(f"{STATIC_PATH}/{path}").read_text()
                mimetype = guess_type(path)[0]
                Logger.trace(f"Serving {STATIC_PATH}{path} ({len(content)} bytes) with mimetype {mimetype})")
                return content, HTTP.OK, {'Content-Type': mimetype}
            except Exception as e:
                Logger.error(f"Error serving file {path}: {e}")
                return "Internal Server Error", HTTP.INTERNAL_SERVER_ERROR

    def __config_api_route(self):
        def list_mc_versions():
            mc_versions = WebInterface.get_mc_versions()
            return [str(version) for version in mc_versions]

        def list_forge_versions(mc_version: str):
            page_path = WebInterface.get_mc_versions()[Version.from_string(mc_version)]
            forge_versions = WebInterface.get_forge_versions(page_path)
            result : dict[str, dict[str, bool]] = {}
            for version, data in forge_versions.items():
                result[str(version)] = {
                    "recommended": data["recommended"],
                    "latest": data["latest"],
                    "bugged": data["bugged"]
                }
            return result
        
        def list_servers():
            servers = self.config.get("servers", default={}, set=True)
            return list(servers.keys())
        
        def get_server_info(server_name: str):
            servers = self.config.get("servers", default={}, set=True)
            if server_name in servers:
                return servers[server_name]
            Logger.trace(f"Server {server_name} not found")
            return "Server Not Found", HTTP.NOT_FOUND

        def create_new_server(server_name: str, mc_version: str, forge_version: str):
            servers = self.config.get("servers", default={}, set=True)
            if server_name in servers:
                Logger.trace(f"Server {server_name} already exists")
                return "Server Already Exists", HTTP.CONFLICT
            servers_path = self.config.get("forge_servers_path")
            server_path = os.path.join(servers_path, server_name)
            self.config.set(f"servers.{server_name}", {
                "mc_version": mc_version,
                "forge_version": forge_version,
                "status": "creating",
                "path": "${forge_servers_path}/" + server_name,
            })
            url = WebInterface.get_forge_installer_url(Version.from_string(mc_version), Version.from_string(forge_version))
            installer.install(url, server_path)
            self.config.set(f"servers.{server_name}.status", "stopped")
            return "Server Created", HTTP.CREATED

        @self.__app.route('/api/<path:path>', methods=['GET'])
        def api_proxy(path):
            try:
                Logger.trace(f"API request for path: {path}")
                if path == "mc_versions":
                    return list_mc_versions()
                elif path.startswith("forge_versions/"):
                    mc_version = path.split("/")[1]
                    return list_forge_versions(mc_version)
                elif path == "servers":
                    return list_servers()
                elif path.startswith("server/"):
                    server_name = path.split("/")[1]
                    return get_server_info(server_name)
                elif path.startswith("create_server"):
                    data = request.args
                    server_name = data.get("name")
                    mc_version = data.get("mc_version")
                    forge_version = data.get("forge_version")
                    if not server_name or not mc_version or not forge_version:
                        Logger.trace("Missing parameters for create_server. got name: {}, path: {}, mc_version: {}, forge_version: {}".format(server_name, server_path, mc_version, forge_version))
                        return "Missing parameters", HTTP.BAD_REQUEST
                    return create_new_server(server_name, mc_version, forge_version)
                else:
                    Logger.trace(f"Unknown API path: {path}")
                    return "Not Found", HTTP.NOT_FOUND
            except Exception as e:
                Logger.error(f"Error processing API request for path {path}: {e}")
                Logger.trace(f"Error details: {traceback.format_exc()}")
                return "Internal Server Error", HTTP.INTERNAL_SERVER_ERROR


    def _get_app(self):
        """
        Get the Flask app instance.
        
        :return: The Flask app instance.
        """
        return self.__app

