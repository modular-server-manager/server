import sys

from gamuLogger import Logger
from eventlet import wsgi
import eventlet
from eventlet import wsgi
import socketio

from .http_server import HttpServer
from .websocket_server import WebSocketServer

Logger.set_module("server")

class Server(HttpServer, WebSocketServer):
    def __init__(self, port: int = 5000, config_path: str = None):
        Logger.trace("Initializing Server")
        HttpServer.__init__(self, port, config_path)
        WebSocketServer.__init__(self, config_path)
    
    def start(self):
        Logger.info(f"Starting HTTP server on port {self._port}")
        try:
            app = socketio.WSGIApp(self._get_sio(), self._get_app())
            wsgi.server(eventlet.listen(('', self._port)), app, log_output=False)
        except KeyboardInterrupt:
            sys.stdout.write("\r")
            sys.stdout.flush()
        except Exception as e:
            Logger.fatal(f"Server encountered an error: {e}")
            sys.exit(1)
        finally:
            Logger.info("HTTP server stopped")