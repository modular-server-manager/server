import sys

from gamuLogger import Logger
from eventlet import wsgi
import eventlet
from eventlet import wsgi
import socketio

from .http_server import HttpServer
from .websocket_server import WebSocketServer

class Server(HttpServer, WebSocketServer):
    def __init__(self, port: int = 5000):
        HttpServer.__init__(self, port)
        WebSocketServer.__init__(self)
    
    def start(self):
        Logger.info(f"Starting HTTP server on port {self._port}")
        app = socketio.WSGIApp(self._get_sio(), self._get_app())
        wsgi.server(eventlet.listen(('', self._port)), app, log_output=False)
        sys.stdout.write("\r")
        Logger.info("HTTP server stopped")