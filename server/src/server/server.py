import sys

import eventlet
import socketio
from eventlet import wsgi
from gamuLogger import Logger

from ..utils.misc import NoLog
from .http_server import HttpServer
from .websocket_server import WebSocketServer

Logger.set_module("server")

class Server(HttpServer, WebSocketServer):
    def __init__(self, config_path: str, port: int = 5000):
        Logger.trace("Initializing Server")
        HttpServer.__init__(self, config_path, port)
        WebSocketServer.__init__(self, config_path)

    def start(self):
        Logger.info(f"Starting HTTP server on port {self._port}")
        try:
            app = socketio.WSGIApp(self._get_sio(), self._get_app())
            wsgi.server(eventlet.listen(('', self._port), reuse_addr=True), app, log=NoLog())
        except KeyboardInterrupt:
            Logger.info("HTTP server stopped by user")
        except Exception as e:
            Logger.fatal(f"Server encountered an error: {e}")
            sys.exit(1)
        finally:
            sys.stdout.write("\r")
            sys.stdout.flush()
            Logger.info("Stopping HTTP server...")
            Logger.info("HTTP server stopped")
