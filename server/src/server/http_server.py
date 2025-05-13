import os
import pathlib
import sys
import traceback
from datetime import datetime, timedelta
from mimetypes import guess_type
from typing import Any

import argon2.exceptions
from flask import Flask, request
from gamuLogger import Logger
from http_code import HttpCode as HTTP
from version import Version

from ..database.types import (AccessLevel, AccessToken, McServer, ServerStatus,
                              User)
from ..forge import installer
from ..forge.web_interface import WebInterface
from ..utils.hash import hash_string, verify_hash
from ..utils.misc import str2bool, time_from_now
from .base_server import STATIC_PATH, BaseServer

Logger.set_module("http_server")


class HttpServer(BaseServer):
    def __init__(self, port: int = 5000, config_path: str = None):
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

    def request_auth(self, access_level: AccessLevel):
        """
        Decorator to check if the user has the required access level.

        :param access_level: Required access level.
        """
        def decorator(f):
            Logger.set_module("middleware")
            def wrapper(*args, **kwargs):
                Logger.info(f"Request from {request.remote_addr} with method {request.method} for path {request.path}")
                try:
                    # check for a server name in parameters (passed with ?server=xxx for GET requests, or in the body for POST requests)
                    server = None
                    if request.method == "GET":
                        server = request.args.get("server", None)
                    elif request.method == "POST":
                        data : dict[str, Any] = request.get_json()
                        if data is not None:
                            server : str = data.get("server")
                    Logger.trace(f"Server name: {server}")

                    if 'Authorization' not in request.headers:
                        Logger.info("Missing Authorization header")
                        return {"message": "Missing parameters"}, HTTP.BAD_REQUEST
                    token = request.headers.get('Authorization')
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
                    if server is None:
                        if user.global_access_level < access_level:
                            Logger.info(f"User {user.username} does not have the required access level")
                            return {"message": "Forbidden"}, HTTP.FORBIDDEN
                    else:
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
                    return f(*args, **kwargs, token=token) # pass the token to the function

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

        @self.__app.route('/app/')
        def index():
            Logger.trace("asking for index.html, redirecting to /app/dashboard.html")
            return static_proxy('dashboard.html')

        @self.__app.route('/app/<path:path>')
        def static_proxy(path):
            try:
                # send the file to the browser
                Logger.trace(f"requesting {STATIC_PATH}/{path}")
                if not os.path.exists(f"{STATIC_PATH}/{path}"):
                    if os.path.exists(f"{STATIC_PATH}/{path}.html"):
                        path = f"{path}.html"
                    else:
                        Logger.trace(f"File not found: {STATIC_PATH}/{path}")
                        return "File not found", HTTP.NOT_FOUND
                content = pathlib.Path(f"{STATIC_PATH}/{path}").read_bytes()
                mimetype = guess_type(path)[0]
                Logger.trace(f"Serving {STATIC_PATH}/{path} ({len(content)} bytes) with mimetype {mimetype})")
                return content, HTTP.OK, {'Content-Type': mimetype}
            except Exception as e:
                Logger.error(f"Error serving file {path}: {e}")
                return "Internal Server Error", HTTP.INTERNAL_SERVER_ERROR


    def __config_api_route(self):

###################################################################################################
# SERVER RELATED ENDPOINTS
# region: server
###################################################################################################

        @self.__app.route('/api/mc_versions', methods=['GET'])
        @self.request_auth(AccessLevel.USER)
        def list_mc_versions():
            Logger.trace(f"API request for path: {request.path}")
            try:
                mc_versions = WebInterface.get_mc_versions()
                return [str(version) for version in mc_versions]
            except Exception as e:
                Logger.error(f"Error processing API request for path {request.path}: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/forge_versions/<path:mc_version>', methods=['GET'])
        @self.request_auth(AccessLevel.USER)
        def list_forge_versions(mc_version: str):
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

        @self.__app.route('/api/servers', methods=['GET'])
        @self.request_auth(AccessLevel.USER)
        def list_servers():
            Logger.trace(f"API request for path: {request.path}")
            try:
                servers = self.config.get("servers", default={}, set=True)
                return list(servers.keys())
            except Exception as e:
                Logger.error(f"Error processing API request for path {request.path}: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/server/<path:server_name>', methods=['GET'])
        @self.request_auth(AccessLevel.USER)
        def get_server_info(server_name: str):
            Logger.trace(f"API request for path: {request.path}")
            try:
                servers = self.config.get("servers", default={}, set=True)
                if server_name in servers:
                    return servers[server_name]
                Logger.trace(f"Server {server_name} not found")
                return {"message": "Server Not Found"}, HTTP.NOT_FOUND
            except Exception as e:
                Logger.error(f"Error processing API request for path {request.path}: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/create_server', methods=['POST'])
        @self.request_auth(AccessLevel.OPERATOR)
        def create_new_server():
            Logger.trace(f"API request for path: {request.path}")
            try:
                data = request.get_json()
                server_name = data.get("name")
                mc_version = data.get("mc_version")
                forge_version = data.get("forge_version")

                if not server_name or not mc_version or not forge_version:
                    Logger.trace("Missing parameters for create_server. got name: {}, path: {}, mc_version: {}, forge_version: {}".format(server_name, server_path, mc_version, forge_version))
                    return {"message": "Missing parameters"}, HTTP.BAD_REQUEST

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
                    status=ServerStatus.STOPPED,
                    path=server_path
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


        @self.__app.route('/api/login', methods=['POST'])
        def login():
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
        def register():
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
        @self.request_auth(AccessLevel.USER)
        def logout(token: str):
            Logger.trace(f"API request for path: {request.path}")
            try:
                self.database.delete_user_token(token)
                return {"message": "Logged out"}, HTTP.OK
            except Exception as e:
                Logger.error(f"Error processing logout request: {e}")
                Logger.debug(f"Error details: {traceback.format_exc()}")
                return {"message" : "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/delete_user', methods=['POST'])
        @self.request_auth(AccessLevel.USER)
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
        @self.request_auth(AccessLevel.USER)
        def get_user_info(token):
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
        @self.request_auth(AccessLevel.USER)
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
        @self.request_auth(AccessLevel.OPERATOR)
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
        @self.request_auth(AccessLevel.OPERATOR)
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
        @self.request_auth(AccessLevel.OPERATOR)
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
        @self.request_auth(AccessLevel.OPERATOR)
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
