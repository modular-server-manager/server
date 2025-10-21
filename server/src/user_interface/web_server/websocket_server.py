import socketio
from gamuLogger import Logger
from typing import Any

from ...bus import BusData
from ..Base_interface import BaseInterface

Logger.set_module("User Interface.WebSock Server")

class WebSocketServer(BaseInterface):
    def __init__(self, bus_data : BusData, database_path: str):
        Logger.trace("Initializing WebSocketServer")
        BaseInterface.__init__(self,
            bus_data=bus_data,
            database_path=database_path
        )
        self.__sio = socketio.Server(cors_allowed_origins='*')
        self.__config_routes()

    def __config_routes(self):
        @self.__sio.event
        def connect(sid, environ):
            Logger.info(f"Client connected: {sid}")

        @self.__sio.event
        def disconnect(sid):
            Logger.info(f"Client disconnected: {sid}")

    def send(self, event: str, data: dict[str, Any]):
        """
        Send a message to all connected clients.

        :param event: The event name to send.
        :param data: The data to send with the event.
        """
        self.__sio.emit(event, data)
        Logger.debug(f"Sent event '{event}' with data: {data}")


    def _get_sio(self):
        """
        Get the SocketIO server instance.

        :return: The SocketIO server instance.
        """
        return self.__sio
