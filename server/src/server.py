from flask import Flask
import eventlet
import pathlib
from eventlet import wsgi
import os
from gamuLogger import Logger
from mimetypes import guess_type

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
            # send the file to the browser
            Logger.trace(f"requesting {STATIC_PATH}/{path}")
            if not os.path.exists(f"{STATIC_PATH}/{path}"):
                Logger.error(f"File not found: {STATIC_PATH}/{path}")
                return "File not found", 404
            content = pathlib.Path(f"{STATIC_PATH}/{path}").read_text()
            mimetype = guess_type(path)[0]
            Logger.trace(f"Serving {STATIC_PATH}{path} ({len(content)} bytes) with mimetype {mimetype})")
            return content, 200, {'Content-Type': mimetype}

    def __config_api_route(self):
        @self.app.route('/api/<path:path>')
        def api_proxy(path):
            # send a 500 error for now
            return f"API not implemented for {path}", 500

    def start(self):
        Logger.info(f"Starting HTTP server on port {self.port}")
        wsgi.server(eventlet.listen(('', self.port)), self.app, log_output=False)
        Logger.info("HTTP server stopped")