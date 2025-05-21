# pyright: reportUnusedFunction=false
# pyright: reportMissingTypeStubs=false

import html
import os
import pathlib
import traceback
from datetime import datetime, timedelta
from mimetypes import guess_type
from typing import Any, Callable, TypeVar

import argon2.exceptions
from flask import Flask, request
from gamuLogger import Logger
from http_code import HttpCode as HTTP
from version import Version

from ...database.types import (AccessLevel, AccessToken, McServer,
                               ServerStatus, User)
from ...minecraft.forge import installer
from ...minecraft.forge.server import ForgeServer
from ...minecraft.forge.web_interface import WebInterface
from ...utils.hash import hash_string, verify_hash
from ...utils.misc import str2bool, time_from_now
from ...utils.regex import RE_MC_SERVER_NAME
from .base_server import STATIC_PATH, BaseServer

Logger.set_module("http_server")

T = TypeVar('T')

JsonAble = dict[str, 'JsonAble'] | list['JsonAble'] | str | int | float | bool | None

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

class HttpServer(BaseServer):
    def __init__(self, config_path: str, port: int = 5000):
        Logger.trace("Initializing HttpServer")
        BaseServer.__init__(self, config_path)
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

    def request_auth(self, access_level: AccessLevel, _global: bool = False) -> Callable[[T], T]:
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
            Logger.set_module("middleware")
            def wrapper(*args: Any, **kwargs: Any) -> FlaskReturnData:
                Logger.info(f"Request from {request.remote_addr} with method {request.method} for path {request.path}")
                try:
                    # check for a server name in parameters (passed with ?server=xxx for GET requests, or in the body for POST requests)
                    server : str|None = None
                    if request.method == "GET":
                        server = request.args.get("server", None)
                    elif request.method == "POST":
                        data : dict[str, JsonAble] | None = request.get_json()
                        if data is not None:
                            if _global:
                                server = None
                            else:
                                _srv = data.get("server")
                                if not isinstance(_srv, str):
                                    Logger.info("Invalid server name")
                                    return {"message": "Invalid parameters"}, HTTP.BAD_REQUEST
                                server = _srv
                    Logger.trace(f"Server name: {server}")

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
                    if not token or not self.database.exist_user_token(token):
                        Logger.info("Invalid token")
                        return {"message": "Invalid token"}, HTTP.UNAUTHORIZED

                    access_token = self.database.get_user_token_by_token(token)
                    if not access_token or not access_token.is_valid():
                        Logger.info("Invalid token")
                        return {"message": "Invalid token"}, HTTP.UNAUTHORIZED

                    user = self.database.get_user(access_token.username)
                    if _global:
                        if user.global_access_level < access_level:
                            Logger.info(f"User {user.username} does not have the required access level")
                            return {"message": "Forbidden"}, HTTP.FORBIDDEN
                    else:
                        if not server:
                            Logger.info("Missing server name")
                            return {"message": "Missing parameters"}, HTTP.BAD_REQUEST
                        server_access_level = self.database.get_user_access(server, user.username)
                        if server_access_level < access_level:
                            Logger.info(f"User {user.username} does not have the required access level for server {server}")
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
                    if "server" in f.__annotations__:
                        additional_args["server"] = server
                    if "user" in f.__annotations__:
                        additional_args["user"] = user
                    return f(*args, **kwargs, **additional_args)

            wrapper.__name__ = f.__name__
            return wrapper

        return decorator

    def __config_static_route(self):
        self.__app.static_folder = STATIC_PATH

        @self.__app.route('/')
        def root():
            # redirect to the app index
            Logger.trace("asking for index, redirecting to /app/")
            return "/redirecting to /app/", HTTP.PERMANENT_REDIRECT, {'Location': '/app/'}

        @self.__app.route('/app/') #pyright: ignore[reportArgumentType, reportUntypedFunctionDecorator]
        def index():
            Logger.trace("asking for index.html, redirecting to /app/dashboard.html")
            return static_proxy('dashboard.html')

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
                    else:
                        Logger.trace(f"File not found: {full_path}")
                        return "File not found", HTTP.NOT_FOUND

                content = pathlib.Path(full_path).read_bytes()
                mimetype = guess_type(path)[0] or 'text/html'
                Logger.trace(f"Serving {STATIC_PATH}/{path} ({len(content)} bytes) with mimetype {mimetype})")
                return content, HTTP.OK, {'Content-Type': mimetype}
            except Exception as e:
                Logger.error(f"Error serving file {path}: {e}")
                return "Internal Server Error", HTTP.INTERNAL_SERVER_ERROR


    def __config_api_route(self):
        self.__config_api_route_user()
        self.__config_api_route_server()



###################################################################################################
# SERVER RELATED ENDPOINTS
# region: server
###################################################################################################
    def __config_api_route_server(self):

        @self.__app.route('/api/mc_versions', methods=['GET']) #pyright: ignore[reportArgumentType, reportUntypedFunctionDecorator]
        @self.request_auth(AccessLevel.USER, _global=True)
        def list_mc_versions() -> FlaskReturnData:
            Logger.trace(f"API request for path: {request.path}")
            try:
                mc_versions = WebInterface.get_mc_versions() # type: ignore
                return {"data" : [str(version) for version in mc_versions]} #type: ignore
            except Exception as e:
                Logger.error(f"Error processing API request for path {request.path}: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/forge_versions/<path:mc_version>', methods=['GET']) #pyright: ignore[reportArgumentType, reportUntypedFunctionDecorator]
        @self.request_auth(AccessLevel.USER, _global=True)
        def list_forge_versions(mc_version: str) -> FlaskReturnData:
            Logger.trace(f"API request for path: {request.path}")
            try:
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
            except Exception as e:
                Logger.error(f"Error processing API request for path {request.path}: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/servers', methods=['GET']) #pyright: ignore[reportArgumentType, reportUntypedFunctionDecorator]
        @self.request_auth(AccessLevel.USER, _global=True)
        def list_servers(token : str) -> FlaskReturnData:
            Logger.trace(f"API request for path: {request.path}")
            try:
                servers = self.database.get_servers()
                result = []
                for server in servers:
                    result.append({
                        "name": server.name,
                        "mc_version": str(server.mc_version),
                        "forge_version": str(server.forge_version),
                        "status": server.status.name
                    })
                return result
            except Exception as e:
                Logger.error(f"Error processing API request for path {request.path}: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/server/<path:server_name>', methods=['GET']) #pyright: ignore[reportArgumentType, reportUntypedFunctionDecorator]
        @self.request_auth(AccessLevel.USER, _global=True)
        def get_server_info(server_name: str) -> FlaskReturnData:
            Logger.trace(f"API request for path: {request.path}")
            try:
                if not self.database.has_server(server_name):
                    Logger.trace(f"Server {server_name} not found")
                    return {"message": "Server Not Found"}, HTTP.NOT_FOUND
                server = self.database.get_server(server_name)

                return {
                    "name": server.name,
                    "mc_version": str(server.mc_version),
                    "forge_version": str(server.forge_version),
                    "status": server.status.name
                }


                Logger.trace(f"Server {server_name} not found")
                return {"message": "Server Not Found"}, HTTP.NOT_FOUND
            except Exception as e:
                Logger.error(f"Error processing API request for path {request.path}: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/create_server', methods=['POST']) #pyright: ignore[reportArgumentType, reportUntypedFunctionDecorator]
        @self.request_auth(AccessLevel.OPERATOR, _global=True)
        def create_new_server() -> FlaskReturnData:
            Logger.trace(f"API request for path: {request.path}")
            try:
                data = request.get_json()
                server_name = data.get("name")
                mc_version = data.get("mc_version")
                forge_version = data.get("forge_version")

                if not server_name or not mc_version or not forge_version:
                    Logger.trace("Missing parameters for create_server. got name: {}, path: {}, mc_version: {}, forge_version: {}".format(server_name, server_path, mc_version, forge_version))
                    return {"message": "Missing parameters"}, HTTP.BAD_REQUEST

                if not RE_MC_SERVER_NAME.match(server_name):
                    Logger.trace(f"Invalid server name: {server_name}")
                    return {"message": "Invalid server name"}, HTTP.BAD_REQUEST

                if not Version.is_valid_string(mc_version):
                    Logger.trace(f"Invalid mc_version: {mc_version}")
                    return {"message": "Invalid mc_version"}, HTTP.BAD_REQUEST

                if not Version.is_valid_string(forge_version):
                    Logger.trace(f"Invalid forge_version: {forge_version}")
                    return {"message": "Invalid forge_version"}, HTTP.BAD_REQUEST

                mc_version = Version.from_string(mc_version)
                forge_version = Version.from_string(forge_version)

                servers = self.config.get("servers", default={}, set=True)
                if server_name in servers:
                    Logger.trace(f"Server {server_name} already exists")
                    return {"message": "Server Already Exists"}, HTTP.CONFLICT
                servers_path = self.config.get("forge_servers_path")
                server_path = os.path.join(servers_path, server_name)

                url = WebInterface.get_forge_installer_url(mc_version, forge_version)
                installer.install(url, server_path)
                srv = McServer(
                    name=server_name,
                    mc_version=mc_version,
                    forge_version=forge_version,
                    status=ServerStatus.STOPPED
                )
                self.database.add_server(srv)
                return {"message": "Server Created"}, HTTP.CREATED
            except Exception as e:
                Logger.error(f"Error creating server: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR


###################################################################################################
# endregion: server
# USER RELATED ENDPOINTS
# region: user
###################################################################################################
    def __config_api_route_user(self):

        @self.__app.route('/api/login', methods=['POST'])
        def login() -> FlaskReturnData:
            Logger.trace(f"API request for path: {request.path}")
            try:
                data = request.get_json()
                username = data.get('username', None)
                password = data.get('password', None)
                remember = str2bool(data.get('remember', 'false'))
                if not username or not password:
                    Logger.trace("Missing parameters for login. got username: {}, password: {}, remember: {}".format(username, password, remember))
                    return {"message": "Missing parameters"}, HTTP.BAD_REQUEST


                if not self.database.has_user(username):
                    Logger.trace(f"User {username} does not exist")
                    return {"message": "Unauthorized"}, HTTP.UNAUTHORIZED
                user = self.database.get_user(username)
                try:
                    if not verify_hash(password, user.password):
                        Logger.trace(f"User {username} provided invalid password")
                        return {"message": "Unauthorized"}, HTTP.UNAUTHORIZED
                except argon2.exceptions.VerifyMismatchError as e:
                    Logger.trace(f"Password verification failed for user {username}: {e}")
                    return {"message": "Unauthorized"}, HTTP.UNAUTHORIZED
                token = AccessToken.new(username, time_from_now(timedelta(hours=1)), remember)
                self.database.set_user_token(token)
                self.database.update_user(User(
                    username=user.username,
                    password=user.password,
                    global_access_level=user.global_access_level,
                    registered_at=user.registered_at,
                    last_login=datetime.now(),
                    last_ip=request.remote_addr
                ))
                Logger.trace(f"User {username} logged in with token {token.token}")
                return { "token": token.token }, HTTP.OK
            except Exception as e:
                Logger.error(f"Error processing login request: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/register', methods=['POST'])
        def register() -> FlaskReturnData:
            print("API request for path: {}".format(request.path))
            Logger.debug(f"API request for path: {request.path}")
            Logger.trace(request.get_json())
            try:
                data = request.get_json()
                username = data.get('username', None)
                password = data.get('password', None)
                remember = str2bool(data.get('remember', 'false'))
                if not username or not password:
                    Logger.debug("Missing parameters for register. got username: {}, password: {}, remember: {}".format(username, password, remember))
                    return {"message": "Missing parameters"}, HTTP.BAD_REQUEST

                password = hash_string(password)

                if self.database.has_user(username):
                    Logger.debug(f"User {username} already exists")
                    return {"message": "User already exists"}, HTTP.CONFLICT

                self.database.add_user(User(
                    username=username,
                    password=password,
                    access_level=AccessLevel.USER,
                    registered_at=datetime.now(),
                    last_login=datetime.now(),
                    last_ip=request.remote_addr
                ))
                token = AccessToken.new(username, time_from_now(timedelta(hours=1)), remember)
                self.database.set_user_token(token)
                Logger.debug(f"User {username} registered with token {token.token}")
                return { "token": token.token }, HTTP.CREATED
            except Exception as e:
                Logger.error(f"Error processing register request: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/logout', methods=['POST'])
        @self.request_auth(AccessLevel.USER, _global=True)
        def logout(token: str) -> FlaskReturnData:
            Logger.trace(f"API request for path: {request.path}")
            try:
                self.database.delete_user_token(token)
                return {"message": "Logged out"}, HTTP.OK
            except Exception as e:
                Logger.error(f"Error processing logout request: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message" : "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/delete_user', methods=['POST'])
        @self.request_auth(AccessLevel.USER, _global=True)
        def delete_user(token: str): # delete the user associated with the token
            Logger.trace(f"API request for path: {request.path}")
            try:
                access_token = self.database.get_user_token_by_token(token)
                if not access_token or not access_token.is_valid():
                    return {"message": "Invalid token"}, HTTP.UNAUTHORIZED

                user = self.database.get_user(access_token.username)
                if not user:
                    return {"message": "User not found"}, HTTP.NOT_FOUND

                self.database.delete_user(user.username)
                self.database.delete_user_token(token)
                return {"message": "User deleted"}, HTTP.OK
            except Exception as e:
                Logger.error(f"Error processing delete user request: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/user', methods=['GET'])
        @self.request_auth(AccessLevel.USER, _global=True)
        def get_user_info(token : str):
            Logger.trace(f"API request for path: {request.path}")
            try:
                if not token:
                    return {"message": "Missing parameters"}, HTTP.BAD_REQUEST

                access_token = self.database.get_user_token_by_token(token)
                if not access_token or not access_token.is_valid():
                    return {"message": "Invalid token"}, HTTP.UNAUTHORIZED

                user = self.database.get_user(access_token.username)
                return {
                    "username": user.username,
                    "access_level": user.global_access_level.name,
                    "registered_at": user.registered_at.strftime("%d/%m/%Y, %H:%M:%S"),
                    "last_login": user.last_login.strftime("%d/%m/%Y, %H:%M:%S"),
                    "last_ip": user.last_ip
                }, HTTP.OK

            except Exception as e:
                Logger.error(f"Error processing user info request: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/user/update_password', methods=['POST'])
        @self.request_auth(AccessLevel.USER, _global=True)
        def update_password(token: str): # update the password of the user associated with the token
            Logger.trace(f"API request for path: {request.path}")
            try:
                access_token = self.database.get_user_token_by_token(token)
                if not access_token or not access_token.is_valid():
                    return {"message": "Invalid token"}, HTTP.UNAUTHORIZED

                user = self.database.get_user(access_token.username)
                data = request.get_json()
                password = data.get('password', None)
                if not password:
                    return {"message": "Missing parameters"}, HTTP.BAD_REQUEST
                user.password = hash_string(password)
                self.database.update_user(user)
                return {"message": "User updated"}, HTTP.OK
            except Exception as e:
                Logger.error(f"Error processing user info request: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/user/<path:username>', methods=['GET'])
        @self.request_auth(AccessLevel.OPERATOR, _global=True)
        def get_user_info_by_username(username: str):
            Logger.trace(f"API request for path: {request.path}")
            try:
                user = self.database.get_user(username)
                if not user:
                    return {"message": "User not found"}, HTTP.NOT_FOUND
                return {
                    "username": user.username,
                    "access_level": user.global_access_level.name,
                    "registered_at": user.registered_at.strftime("%d/%m/%Y, %H:%M:%S"),
                    "last_login": user.last_login.strftime("%d/%m/%Y, %H:%M:%S"),
                    "last_ip": user.last_ip
                }, HTTP.OK
            except Exception as e:
                Logger.error(f"Error processing user info request: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/user/<path:username>/global_access', methods=['POST'])
        @self.request_auth(AccessLevel.OPERATOR, _global=True)
        def update_user_global_access(username: str): # update the global access level of the user
            Logger.trace(f"API request for path: {request.path}")
            try:
                data = request.get_json()
                access_level = data.get('access_level', None)
                if not access_level:
                    return {"message": "Missing parameters"}, HTTP.BAD_REQUEST
                user = self.database.get_user(username)
                if not user:
                    return {"message": "User not found"}, HTTP.NOT_FOUND
                user.global_access_level = AccessLevel[access_level]
                self.database.update_user(user)
                return {"message": "User updated"}, HTTP.OK
            except Exception as e:
                Logger.error(f"Error processing user info request: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/user/<path:username>/password', methods=['POST'])
        @self.request_auth(AccessLevel.OPERATOR, _global=True)
        def update_user_password(username: str):
            Logger.trace(f"API request for path: {request.path}")
            try:
                data = request.get_json()
                password = data.get('password', None)
                if not password:
                    return {"message": "Missing parameters"}, HTTP.BAD_REQUEST
                user = self.database.get_user(username)
                if not user:
                    return {"message": "User not found"}, HTTP.NOT_FOUND
                user.password = hash_string(password)
                self.database.update_user(user)
                return {"message": "User updated"}, HTTP.OK
            except Exception as e:
                Logger.error(f"Error processing user info request: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/user/<path:username>/access', methods=['POST'])
        @self.request_auth(AccessLevel.OPERATOR, _global=True)
        def update_user_access(username: str): # update the access level of the user for a specific server
            Logger.trace(f"API request for path: {request.path}")
            try:
                data = request.get_json()
                server = data.get('server', None)
                access_level = data.get('access_level', None)
                if not server or not access_level:
                    return {"message": "Missing parameters"}, HTTP.BAD_REQUEST
                user = self.database.get_user(username)
                if not user:
                    return {"message": "User not found"}, HTTP.NOT_FOUND
                server_access_level = AccessLevel[access_level]
                self.database.set_user_access(server, username, server_access_level)
                return {"message": "User updated"}, HTTP.OK
            except Exception as e:
                Logger.error(f"Error processing user info request: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR


###################################################################################################
# endregion: user
###################################################################################################
