import socketio
from gamuLogger import Logger



class WebSocketServer:
    def __init__(self):
        self.__sio = socketio.Server(cors_allowed_origins='*')
        self.__config_routes()

    def __config_routes(self):
        @self.__sio.event
        def connect(sid, environ):
            Logger.info(f"Client connected: {sid}")

        @self.__sio.event
        def disconnect(sid):
            Logger.info(f"Client disconnected: {sid}")
            
    def send(self, event: str, data: dict):
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