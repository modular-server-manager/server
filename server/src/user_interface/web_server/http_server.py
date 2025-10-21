# pyright: reportUnusedFunction=false
# pyright: reportMissingTypeStubs=false

import html
import os
import pathlib
import traceback
from typing import Any, Callable, TypeVar, Union

from flask import Flask, request
from gamuLogger import Logger
from http_code import HttpCode as HTTP
from version import Version

from ...utils.misc import str2bool, guess_type  # must be moved to a user-interface utils module
from ...utils.regex import RE_MC_SERVER_NAME    # must be moved to a user-interface utils module
from ..Base_interface import BaseInterface      # will be changed to be an external dependency
from ..database.types import AccessLevel        # will be changed to be an external dependency

Logger.set_module("User Interface.Http Server")

STATIC_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "/client"

T = TypeVar('T')

# type JsonAble = dict[str, JsonAble] | list[JsonAble] | str | int | float | bool | None
JsonAble = Union[dict[str, Any], list[Any], str, int, float, bool, None]

FlaskReturnData = (
    tuple[JsonAble, int, dict[str, str]] |      # data, status code, headers
    tuple[JsonAble, int] |                      # data, status code
    tuple[JsonAble] |                           # data
    JsonAble |                                  # data

    tuple[str, int, dict[str, str]] |           # string, status code, headers
    tuple[str, int] |                           # string, status code
    tuple[str] |                                # string
    str                                         # string
)

class HttpServer(BaseInterface):
    def __init__(self, *args: Any, port: int, **kwargs: Any):
        Logger.trace("Initializing HttpServer")
        BaseInterface.__init__(self, *args, **kwargs)
        self._port = port
        self.__app = Flask(__name__)

        self.__config_api_route()
        self.__config_static_route()

    def _get_app(self):
        """
        Get the Flask app instance.

        :return: The Flask app instance.
        """
        return self.__app

    def request_auth(self, access_level: AccessLevel) -> Callable[[T], T]:
        """
        Decorator to check if the user has the required access level.

        Can expose the token, server name and user object to the function.
        - token: the token used to authenticate the user
        - server: the server name passed in the request
        - user: the user object associated with the token

        **The type hints for the function must be set for the decorator to work properly.**

        :param access_level: Required access level.
        """
        def decorator(f : Callable[[Any], FlaskReturnData] | Callable[[], FlaskReturnData]) -> Callable[[Any], FlaskReturnData] | Callable[[], FlaskReturnData]:
            def wrapper(*args: Any, **kwargs: Any) -> FlaskReturnData:
                Logger.info(f"Request from {request.remote_addr} with method {request.method} for path {request.path}")
                try:
                    if 'Authorization' not in request.headers:
                        Logger.info("Missing Authorization header")
                        return {"message": "Missing parameters"}, HTTP.BAD_REQUEST
                    token = request.headers.get('Authorization')
                    if not token:
                        Logger.info("Missing Authorization header")
                        return {"message": "Missing parameters"}, HTTP.BAD_REQUEST
                    if not token.startswith("Bearer "):
                        Logger.info("Invalid Authorization header format")
                        return {"message": "Invalid token"}, HTTP.UNAUTHORIZED
                    token = token[7:]
                    if not token or not self._database.exist_user_token(token):
                        Logger.info("Invalid token")
                        return {"message": "Invalid token"}, HTTP.UNAUTHORIZED

                    access_token = self._database.get_user_token_by_token(token)
                    if not access_token or not access_token.is_valid():
                        Logger.info("Invalid token")
                        return {"message": "Invalid token"}, HTTP.UNAUTHORIZED

                    user = self._database.get_user(access_token.username)
                    if user.access_level < access_level:
                        Logger.info(f"User {user.username} does not have the required access level")
                        return {"message": "Forbidden"}, HTTP.FORBIDDEN
                except Exception as e:
                    Logger.error(f"Error processing request: {e}")
                    Logger.debug(f"Error details: {traceback.format_exc()}")
                    return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR
                else:
                    Logger.info(f"User {user.username} has the required access level")
                    additional_args = {}
                    if "token" in f.__annotations__:
                        additional_args["token"] = token
                    if "user" in f.__annotations__:
                        additional_args["user"] = user
                    return f(*args, **kwargs, **additional_args)

            wrapper.__name__ = f.__name__
            return wrapper

        return decorator # type: ignore

    def __config_static_route(self):
        self.__app.static_folder = STATIC_PATH

        @self.__app.route('/')
        def root():
            # redirect to the app index
            Logger.trace("asking for index, redirecting to /app/")
            return "/redirecting to /app/", HTTP.PERMANENT_REDIRECT, {'Location': '/app/'}

        @self.__app.route('/app/') #pyright: ignore[reportArgumentType, reportUntypedFunctionDecorator]
        def index():
            Logger.trace("asking for index.html, redirecting to /app/dashboard")
            return static_proxy('dashboard')

        @self.__app.route('/app/<path:path>') #pyright: ignore[reportArgumentType, reportUntypedFunctionDecorator]
        def static_proxy(path : str):
            try:
                # Validate the path to prevent directory traversal attacks
                if ".." in path or path.startswith("/"):
                    Logger.trace(f"Invalid path: {path}")
                    return "Invalid path", HTTP.BAD_REQUEST

                # send the file to the browser
                Logger.trace(f"requesting {STATIC_PATH}/{path}")
                # Normalize the path and ensure it is within STATIC_PATH
                full_path = os.path.normpath(os.path.join(STATIC_PATH, path))
                if not full_path.startswith(STATIC_PATH):
                    Logger.trace(f"Invalid path traversal attempt: {path}")
                    return "Invalid path", HTTP.BAD_REQUEST

                if not os.path.exists(full_path):
                    if os.path.exists(f"{full_path}.html"):
                        full_path = f"{full_path}.html"
                    # elif full_path.endswith('.css') or full_path.endswith('.js'):
                    elif any(full_path.endswith(ext) for ext in ['.css', '.js', '.css.map']):
                        # /client/login.js -> /client/login/login.js
                        filename = '.'.join(os.path.basename(full_path).split('.')[:-1])
                        full_path = os.path.join(os.path.dirname(full_path), filename, os.path.basename(full_path))
                        if not os.path.exists(full_path):
                            Logger.trace(f"File not found: {full_path}")
                            return "File not found", HTTP.NOT_FOUND
                    else:
                        Logger.trace(f"File not found: {full_path}")
                        return "File not found", HTTP.NOT_FOUND
                
                if os.path.isdir(full_path):
                    # If the path is a directory, serve the index.html file inside it
                    index_file = os.path.join(full_path, 'index.html')
                    if os.path.exists(index_file):
                        full_path = index_file
                    else:
                        Logger.trace(f"Directory requested without index file: {full_path}")
                        return "Directory requested without index file", HTTP.BAD_REQUEST
                Logger.trace(f"Serving file: {full_path}")

                content = pathlib.Path(full_path).read_bytes()
                mimetype = guess_type(full_path)
                # Only allow known-safe mimetypes
                Logger.trace(f"Serving {STATIC_PATH}/{path} ({len(content)} bytes) with mimetype {mimetype})")
                return content, HTTP.OK, {'Content-Type': mimetype}
            except Exception as e:
                Logger.error(f"Error serving file {path}: {e}")
                return "Internal Server Error", HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/<path:path>') #pyright: ignore[reportArgumentType, reportUntypedFunctionDecorator]
        def static_fallback(path: str):
            """
            Fallback route for static files.
            This will serve files from the static folder if they exist.
            """
            Logger.trace(f"Fallback for static file: {path}")
            return static_proxy(path)

    def __config_api_route(self):
        self.__config_api_route_user()
        self.__config_api_route_server()



###################################################################################################
# SERVER RELATED ENDPOINTS
# region: server
###################################################################################################
    def __config_api_route_server(self):

        @self.__app.route('/api/mc_versions', methods=['GET']) #pyright: ignore[reportArgumentType, reportUntypedFunctionDecorator]
        @self.request_auth(AccessLevel.USER)
        def list_mc_versions() -> FlaskReturnData:
            Logger.trace(f"API request for path: {request.path}")
            try:
                versions = self.list_mc_versions()
                return {"versions": [str(version) for version in versions]}, HTTP.OK
            except Exception as e:
                Logger.error(f"Error processing API request for path {request.path}: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/forge_versions/<path:mc_version>', methods=['GET']) #pyright: ignore[reportArgumentType, reportUntypedFunctionDecorator]
        @self.request_auth(AccessLevel.USER)
        def list_forge_versions(mc_version: str) -> FlaskReturnData:
            Logger.trace(f"API request for path: {request.path}")
            try:
                if not Version.is_valid_string(mc_version):
                    Logger.trace(f"Invalid mc_version: {mc_version}")
                    return {"message": "Invalid mc_version"}, HTTP.BAD_REQUEST
                mc_version_v = Version.from_string(mc_version)
                versions = self.list_forge_versions(mc_version_v)
                return {"versions": [str(version) for version in versions]}, HTTP.OK
            except Exception as e:
                Logger.error(f"Error processing API request for path {request.path}: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/servers', methods=['GET']) #pyright: ignore[reportArgumentType, reportUntypedFunctionDecorator]
        @self.request_auth(AccessLevel.USER)
        def list_servers(token : str) -> FlaskReturnData:
            Logger.trace(f"API request for path: {request.path}")
            try:
                servers = self.list_servers()
                result = []
                for server in servers:
                    for key, item in server.items():
                        if isinstance(item, Version):
                            server[key] = str(item)
                    result.append(server)
                return result
            except ValueError as ve:
                Logger.debug(f"Error processing API request for path {request.path}: {ve}")
                return {"message": "Bad Request"}, HTTP.BAD_REQUEST
            except Exception as e:
                Logger.error(f"Error processing API request for path {request.path}: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/server/<path:server_name>', methods=['GET']) #pyright: ignore[reportArgumentType, reportUntypedFunctionDecorator]
        @self.request_auth(AccessLevel.USER)
        def get_server_info(server_name: str) -> FlaskReturnData:
            Logger.trace(f"API request for path: {request.path}")
            try:
                info = self.get_server_info(server_name)
                for key, item in info.items():
                    if isinstance(item, Version):
                        info[key] = str(item)
                return info, HTTP.OK
            except ValueError as ve:
                Logger.debug(f"Error processing API request for path {request.path}: {ve}")
                return {"message": "Bad Request"}, HTTP.BAD_REQUEST
            except Exception as e:
                Logger.error(f"Error processing API request for path {request.path}: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/list_mc_server_dirs', methods=['GET']) #pyright: ignore[reportArgumentType, reportUntypedFunctionDecorator]
        @self.request_auth(AccessLevel.USER)
        def list_mc_server_dirs(token : str) -> FlaskReturnData:
            Logger.trace(f"API request for path: {request.path}")
            try:
                dirs = self.list_mc_server_dirs()
                return {"dirs": dirs}, HTTP.OK
            except Exception as e:
                Logger.error(f"Error processing API request for path {request.path}: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/create_server', methods=['POST']) #pyright: ignore[reportArgumentType, reportUntypedFunctionDecorator]
        @self.request_auth(AccessLevel.OPERATOR)
        def create_new_server() -> FlaskReturnData:
            Logger.trace(f"API request for path: {request.path}")
            try:
                data : dict[str, JsonAble] = request.get_json()
                server_name = data.get("name")
                server_type = data.get("type")
                server_path = data.get("path")
                
                autostart = data.get("autostart", False)
                
                mc_version = data.get("mc_version")
                modloader_version = data.get("modloader_version")
                ram = data.get("ram")

                if not server_name or not isinstance(server_name, str) or not RE_MC_SERVER_NAME.match(server_name):
                    Logger.debug("Invalid server name")
                    return {"message": "Invalid parameters"}, HTTP.BAD_REQUEST
                server_name = html.escape(server_name.strip())
                if not server_type or not isinstance(server_type, str):
                    Logger.debug("Invalid server type")
                    return {"message": "Invalid parameters"}, HTTP.BAD_REQUEST

                if not server_path or not isinstance(server_path, str):
                    Logger.debug("Invalid server path")
                    return {"message": "Invalid parameters"}, HTTP.BAD_REQUEST
                server_path = html.escape(server_path.strip())
                if not mc_version or not isinstance(mc_version, str):
                    Logger.debug("Invalid mc_version")
                    return {"message": "Invalid parameters"}, HTTP.BAD_REQUEST
                mc_version = Version.from_string(mc_version)
                if server_type != "vanilla" and not modloader_version or not isinstance(modloader_version, str):
                    Logger.debug("Invalid modloader_version")
                    return {"message": "Invalid parameters"}, HTTP.BAD_REQUEST
                if not modloader_version:
                    Logger.debug("Modloader version is required for non-vanilla servers")
                    return {"message": "Invalid parameters"}, HTTP.BAD_REQUEST
                modloader_version = Version.from_string(modloader_version)
                if not isinstance(autostart, bool):
                    Logger.debug("Invalid autostart value")
                    return {"message": "Invalid parameters"}, HTTP.BAD_REQUEST
                if not isinstance(ram, int) or ram <= 0:
                    Logger.debug("Invalid RAM value")
                    return {"message": "Invalid parameters"}, HTTP.BAD_REQUEST

                self.create_server(
                    name=server_name,
                    type=server_type,
                    path=server_path,
                    autostart=autostart,
                    mc_version=mc_version,
                    modloader_version=modloader_version,
                    ram=ram
                )
            except ValueError as ve:
                Logger.debug(f"Error creating server: {ve}")
                return {"message": "Bad Request"}, HTTP.BAD_REQUEST
            except Exception as e:
                Logger.error(f"Error creating server: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/start_server/<path:server_name>', methods=['POST']) #pyright: ignore[reportArgumentType, reportUntypedFunctionDecorator]
        @self.request_auth(AccessLevel.ADMIN)
        def start_server(server_name: str) -> FlaskReturnData:
            Logger.trace(f"API request for path: {request.path}")
            try:
                self.start_server(server_name)
                return {"message": "Server started"}, HTTP.OK
            except ValueError as ve:
                Logger.debug(f"Start server error: {ve}")
                return {"message": "Bad Request"}, HTTP.BAD_REQUEST
            except Exception as e:
                Logger.error(f"Error starting server: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/stop_server/<path:server_name>', methods=['POST']) #pyright: ignore[reportArgumentType, reportUntypedFunctionDecorator]
        @self.request_auth(AccessLevel.ADMIN)
        def stop_server(server_name: str) -> FlaskReturnData:
            Logger.trace(f"API request for path: {request.path}")
            try:
                self.stop_server(server_name)
                return {"message": "Server stopped"}, HTTP.OK
            except ValueError as ve:
                Logger.debug(f"Stop server error: {ve}")
                return {"message": "Bad Request"}, HTTP.BAD_REQUEST
            except Exception as e:
                Logger.error(f"Error stopping server: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/restart_server/<path:server_name>', methods=['POST']) #pyright: ignore[reportArgumentType, reportUntypedFunctionDecorator]
        @self.request_auth(AccessLevel.ADMIN)
        def restart_server(server_name: str) -> FlaskReturnData:
            Logger.trace(f"API request for path: {request.path}")
            try:
                self.restart_server(server_name)
                return {"message": "Server restarted"}, HTTP.OK
            except ValueError as ve:
                Logger.debug(f"Restart server error: {ve}")
                return {"message": "Bad Request"}, HTTP.BAD_REQUEST
            except Exception as e:
                Logger.error(f"Error restarting server: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

###################################################################################################
# endregion: server
# USER RELATED ENDPOINTS
# region: user
###################################################################################################
    def __config_api_route_user(self):

        @self.__app.route('/api/login', methods=['POST']) #pyright: ignore[reportArgumentType]
        def login() -> FlaskReturnData:
            Logger.trace(f"API request for path: {request.path}")
            try:
                data = request.get_json()
                username = data.get('username', None)
                password = data.get('password', None)
                remember = str2bool(data.get('remember', 'false'))
                token = self.login(username, password, remember)
                return {"token": token.token}, HTTP.OK
            except ValueError as ve:
                Logger.debug(f"Login error: {ve}")
                return {"message": "Bad Request"}, HTTP.BAD_REQUEST
            except Exception as e:
                Logger.error(f"Error processing login request: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/register', methods=['POST']) #pyright: ignore[reportArgumentType]
        def register() -> FlaskReturnData:
            Logger.debug(f"API request for path: {request.path}")
            Logger.trace(request.get_json())
            try:
                data = request.get_json()
                username = data.get('username', None)
                password = data.get('password', None)
                remember = str2bool(data.get('remember', 'false'))
                token = self.register(username, password, remember)
                return { "token": token.token }, HTTP.CREATED
            except ValueError as ve:
                Logger.debug(f"Register error: {ve}")
                return {"message": "Bad Request"}, HTTP.BAD_REQUEST
            except Exception as e:
                Logger.error(f"Error processing register request: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/logout', methods=['POST']) #pyright: ignore[reportArgumentType]
        @self.request_auth(AccessLevel.USER)
        def logout(token: str) -> FlaskReturnData:
            Logger.trace(f"API request for path: {request.path}")
            try:
                self.logout(token)
                return {"message": "Logged out"}, HTTP.OK
            except ValueError as ve:
                Logger.debug(f"Logout error: {ve}")
                return {"message": "Bad Request"}, HTTP.BAD_REQUEST
            except Exception as e:
                Logger.error(f"Error processing logout request: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message" : "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/delete_user', methods=['POST'])
        @self.request_auth(AccessLevel.USER)
        def delete_user(token: str): # delete the user associated with the token
            Logger.trace(f"API request for path: {request.path}")
            try:
                self.delete_user(token)
                return {"message": "User deleted"}, HTTP.OK
            except ValueError as ve:
                Logger.debug(f"Delete user error: {ve}")
                return {"message": "Bad Request"}, HTTP.BAD_REQUEST
            except Exception as e:
                Logger.error(f"Error processing delete user request: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/user', methods=['GET'])
        @self.request_auth(AccessLevel.USER)
        def get_user_info(token : str):
            Logger.trace(f"API request for path: {request.path}")
            try:
                user = self.get_user_info(token)
                return {
                    "username": user.username,
                    "access_level": user.access_level.name,
                    "registered_at": user.registered_at.strftime("%d/%m/%Y, %H:%M:%S"),
                    "last_login": user.last_login.strftime("%d/%m/%Y, %H:%M:%S")
                }, HTTP.OK
            except ValueError as ve:
                Logger.debug(f"Get user info error: {ve}")
                return {"message": "Bad Request"}, HTTP.BAD_REQUEST
            except Exception as e:
                Logger.error(f"Error processing user info request: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/user/update_password', methods=['POST'])
        @self.request_auth(AccessLevel.USER)
        def update_password(token: str): # update the password of the user associated with the token
            Logger.trace(f"API request for path: {request.path}")
            try:
                data = request.get_json()
                password = data.get('password', None)
                self.update_password(token, password)
                return {"message": "User updated"}, HTTP.OK
            except ValueError as ve:
                Logger.debug(f"Update password error: {ve}")
                return {"message": "Bad Request"}, HTTP.BAD_REQUEST
            except Exception as e:
                Logger.error(f"Error processing user info request: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/user/<path:username>', methods=['GET'])
        @self.request_auth(AccessLevel.OPERATOR)
        def get_user_info_by_username(username: str):
            Logger.trace(f"API request for path: {request.path}")
            try:
                user = self.get_user_info_by_username(username)
                return {
                    "username": user.username,
                    "access_level": user.access_level.name,
                    "registered_at": user.registered_at.strftime("%d/%m/%Y, %H:%M:%S"),
                    "last_login": user.last_login.strftime("%d/%m/%Y, %H:%M:%S")
                }, HTTP.OK
            except ValueError as ve:
                Logger.debug(f"Get user info by username error: {ve}")
                return {"message": "Bad Request"}, HTTP.BAD_REQUEST
            except Exception as e:
                Logger.error(f"Error processing user info request: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/user/<path:username>/global_access', methods=['POST'])
        @self.request_auth(AccessLevel.OPERATOR)
        def update_user_global_access(username: str): # update the global access level of the user
            Logger.trace(f"API request for path: {request.path}")
            try:
                data = request.get_json()
                access_level = data.get('access_level', None)
                self.update_user_access(username, access_level)
                return {"message": "User updated"}, HTTP.OK
            except ValueError as ve:
                Logger.debug(f"Update user global access error: {ve}")
                return {"message": "Bad Request"}, HTTP.BAD_REQUEST
            except Exception as e:
                Logger.error(f"Error processing user info request: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/user/<path:username>/password', methods=['POST'])
        @self.request_auth(AccessLevel.OPERATOR)
        def update_user_password(username: str):
            Logger.trace(f"API request for path: {request.path}")
            try:
                data = request.get_json()
                password = data.get('password', None)
                self.update_user_password(username, password)
                return {"message": "User updated"}, HTTP.OK
            except ValueError as ve:
                Logger.debug(f"Update user password error: {ve}")
                return {"message": "Bad Request"}, HTTP.BAD_REQUEST
            except Exception as e:
                Logger.error(f"Error processing user info request: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

###################################################################################################
# endregion: user
###################################################################################################
