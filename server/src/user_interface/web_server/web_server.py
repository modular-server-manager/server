import sys
from datetime import datetime

import eventlet
import socketio
from eventlet import wsgi
from gamuLogger import Logger
from version import Version
from typing import Any

from .utils import NoLog
from .http_server import HttpServer
from .websocket_server import WebSocketServer

Logger.set_module("User Interface.Web Server")

class WebServer(HttpServer, WebSocketServer):
    def __init__(self, *args: Any, **kwargs: Any):
        Logger.trace("Initializing WebServer")
        HttpServer.__init__(self,
            *args,
            **kwargs
        )
        WebSocketServer.__init__(self,
            *args,
            **kwargs
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


####################################### EVENT TRANSMISSION ########################################

    def on_server_starting(self, timestamp: datetime, server_name: str) -> None:
        self.send("server_starting", {
            "timestamp": timestamp.isoformat(),
            "server_name": server_name
        })
    
    def on_server_started(self, timestamp: datetime, server_name: str) -> None:
        self.send("server_started", {
            "timestamp": timestamp.isoformat(),
            "server_name": server_name
        })
    
    def on_server_stopping(self, timestamp: datetime, server_name: str) -> None:
        self.send("server_stopping", {
            "timestamp": timestamp.isoformat(),
            "server_name": server_name
        })
    
    def on_server_stopped(self, timestamp: datetime, server_name: str) -> None:
        self.send("server_stopped", {
            "timestamp": timestamp.isoformat(),
            "server_name": server_name
        })
    
    def on_server_crashed(self, timestamp: datetime, server_name: str) -> None:
        self.send("server_crashed", {
            "timestamp": timestamp.isoformat(),
            "server_name": server_name
        })
    
    def on_server_created(self, timestamp: datetime, server_name: str, server_type: str, server_path: str, autostart: bool, mc_version: Version, modloader_version: Version, ram: int) -> None:
        self.send("server_created", {
            "timestamp": timestamp.isoformat(),
            "server_name": server_name,
            "server_type": server_type,
            "server_path": server_path,
            "autostart": autostart,
            "mc_version": mc_version,
            "modloader_version": modloader_version,
            "ram": ram
        })
    
    def on_server_deleted(self, timestamp: datetime, server_name: str) -> None:
        self.send("server_deleted", {
            "timestamp": timestamp.isoformat(),
            "server_name": server_name
        })
    
    def on_server_renamed(self, timestamp: datetime, old_name: str, new_name: str) -> None:
        self.send("server_renamed", {
            "timestamp": timestamp.isoformat(),
            "old_name": old_name,
            "new_name": new_name
        })
    
    def on_console_message_received(self, timestamp: datetime, server_name: str, message: str) -> None:
        self.send("console_message_received", {
            "timestamp": timestamp.isoformat(),
            "server_name": server_name,
            "message": message
        })
    
    def on_console_log_received(self, timestamp: datetime, server_name: str, log: str) -> None:
        self.send("console_log_received", {
            "timestamp": timestamp.isoformat(),
            "server_name": server_name,
            "log": log
        })
    
    def on_player_joined(self, timestamp: datetime, server_name: str, player_name: str) -> None:
        self.send("player_joined", {
            "timestamp": timestamp.isoformat(),
            "server_name": server_name,
            "player_name": player_name
        })
    
    def on_player_left(self, timestamp: datetime, server_name: str, player_name: str) -> None:
        self.send("player_left", {
            "timestamp": timestamp.isoformat(),
            "server_name": server_name,
            "player_name": player_name
        })
    
    def on_player_kicked(self, timestamp: datetime, server_name: str, player_name: str, reason: str) -> None:
        self.send("player_kicked", {
            "timestamp": timestamp.isoformat(),
            "server_name": server_name,
            "player_name": player_name,
            "reason": reason
        })
    
    def on_player_banned(self, timestamp: datetime, server_name: str, player_name: str, reason: str) -> None:
        self.send("player_banned", {
            "timestamp": timestamp.isoformat(),
            "server_name": server_name,
            "player_name": player_name,
            "reason": reason
        })
    
    def on_player_pardoned(self, timestamp: datetime, server_name: str, player_name: str) -> None:
        self.send("player_pardoned", {
            "timestamp": timestamp.isoformat(),
            "server_name": server_name,
            "player_name": player_name
        })
