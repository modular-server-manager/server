from flask import Flask
import eventlet
import pathlib
from eventlet import wsgi
import os
from gamuLogger import Logger
from mimetypes import guess_type

from .forge_web_interface import WebInterface
from .version import Version

Logger.set_module("server")

BASE_PATH = __file__[:__file__.rfind('/')] # get the base path of the server

STATIC_PATH = f'{BASE_PATH}/client'


class HttpServer:
    def __init__(self, port: int = 5000):
        self.port = port
        self.app = Flask(__name__)
        
        self.__config_api_route()
        self.__config_static_route()
        
    def __config_static_route(self):
        @self.app.route('/')
        def index():
            return static_proxy('index.html')
            

        @self.app.route('/<path:path>')
        def static_proxy(path):
            try:
                # send the file to the browser
                Logger.trace(f"requesting {STATIC_PATH}/{path}")
                if not os.path.exists(f"{STATIC_PATH}/{path}"):
                    Logger.trace(f"File not found: {STATIC_PATH}/{path}")
                    return "File not found", 404
                content = pathlib.Path(f"{STATIC_PATH}/{path}").read_text()
                mimetype = guess_type(path)[0]
                Logger.trace(f"Serving {STATIC_PATH}{path} ({len(content)} bytes) with mimetype {mimetype})")
                return content, 200, {'Content-Type': mimetype}
            except Exception as e:
                Logger.error(f"Error serving file {path}: {e}")
                return "Internal Server Error", 500

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


        @self.app.route('/api/<path:path>')
        def api_proxy(path):
            try:
                Logger.trace(f"API request for path: {path}")
                if path == "mc_versions":
                    return list_mc_versions()
                elif path.startswith("forge_versions/"):
                    mc_version = path.split("/")[1]
                    return list_forge_versions(mc_version)
                else:
                    Logger.trace(f"Unknown API path: {path}")
                    return "Not Found", 404
            except Exception as e:
                Logger.error(f"Error processing API request for path {path}: {e}")
                return "Internal Server Error", 500

    def start(self):
        Logger.info(f"Starting HTTP server on port {self.port}")
        wsgi.server(eventlet.listen(('', self.port)), self.app, log_output=False)
        Logger.info("HTTP server stopped")