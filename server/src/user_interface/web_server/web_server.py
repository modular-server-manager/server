import sys

import eventlet
import socketio
from eventlet import wsgi
from gamuLogger import Logger

from ...bus import BusData
from ...utils.misc import NoLog
from ..Base_interface import BaseInterface
from .http_server import HttpServer
from .websocket_server import WebSocketServer

Logger.set_module("server")

class WebServer(HttpServer, WebSocketServer):
    def __init__(self, bus_data : BusData, database_path: str, port: int = 5000):
        Logger.trace("Initializing WebServer")
        HttpServer.__init__(self,
            bus_data=bus_data,
            database_path=database_path,
            port=port
        )
        WebSocketServer.__init__(self,
            bus_data=bus_data,
            database_path=database_path
        )

    def start(self):
        super().start()
        Logger.info(f"Starting HTTP server on port {self._port}")
        try:
            app = socketio.WSGIApp(self._get_sio(), self._get_app())
            wsgi.server(eventlet.listen(('', self._port), reuse_addr=True), app, log=NoLog())
        except KeyboardInterrupt:
            Logger.info("HTTP server stopped by user")
        except Exception as e:
            Logger.fatal(f"WebServer encountered an error: {e}")
            sys.exit(1)
        finally:
            sys.stdout.write("\r")
            sys.stdout.flush()
            Logger.info("Stopping HTTP server...")
            Logger.info("HTTP server stopped")

    def stop(self):
        Logger.info("Stopping WebServer...")
        HttpServer.stop(self)
        WebSocketServer.stop(self)
        Logger.info("WebServer stopped")
