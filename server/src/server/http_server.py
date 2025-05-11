from flask import Flask, request
import pathlib
import os
from gamuLogger import Logger
from http_code import HttpCode as HTTP

from mimetypes import guess_type
import traceback
from datetime import timedelta

from ..forge.web_interface import WebInterface
from version import Version
from ..utils.hash import hash_string
from ..utils.misc import str2bool, time_from_now
from ..forge import installer
from .database import McServer, ServerStatus, AccessLevel, User, AccessToken
from .base_server import BaseServer, STATIC_PATH

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
                    if user.access_level < access_level:
                        Logger.info(f"User {user.username} does not have the required access level")
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
        def index():
            # redirect to the app index
            Logger.trace("asking for index, redirecting to /app/")
            return "/redirecting to /app/", HTTP.PERMANENT_REDIRECT, {'Location': '/app/'}

        @self.__app.route('/app/')
        def app_index():
            Logger.trace("asking for index.html, redirecting to /app/index.html")
            return static_proxy('index.html')

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
                Logger.trace(f"Error details: {traceback.format_exc()}")
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
                Logger.trace(f"Error details: {traceback.format_exc()}")
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
                Logger.trace(f"Error details: {traceback.format_exc()}")
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
                Logger.trace(f"Error details: {traceback.format_exc()}")
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
                Logger.trace(f"Error details: {traceback.format_exc()}")
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
                username = data.get('username')
                password = data.get('password')
                remember = str2bool(data.get('remember', 'false'))
                if not username or not password:
                    Logger.trace("Missing parameters for login. got username: {}, password: {}, remember: {}".format(username, password, remember))
                    return {"message": "Missing parameters"}, HTTP.BAD_REQUEST

                password = hash_string(password)

                if not self.database.has_user(username):
                    Logger.trace(f"User {username} does not exist")
                    return {"message": "Unauthorized"}, HTTP.UNAUTHORIZED
                user = self.database.get_user(username)
                if user.password != password:
                    Logger.trace(f"User {username} provided invalid password")
                    return {"message": "Unauthorized"}, HTTP.UNAUTHORIZED
                token = AccessToken.new(username, time_from_now(timedelta(hours=1)), remember)
                self.database.set_user_token(token)
                Logger.trace(f"User {username} logged in with token {token.token}")
                return { "token": token.token }, HTTP.OK
            except Exception as e:
                Logger.error(f"Error processing login request: {e}")
                Logger.trace(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR
        
        @self.__app.route('/api/register', methods=['POST'])
        def register():
            Logger.debug(f"API request for path: {request.path}")
            Logger.trace(request.get_json())
            try:
                data = request.get_json()
                username = data.get('username')
                password = data.get('password')
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
                    access_level=AccessLevel.USER
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
                Logger.trace(f"Error details: {traceback.format_exc()}")
                return {"message" : "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR

        @self.__app.route('/api/user', methods=['GET'])
        @self.request_auth(AccessLevel.USER)
        def get_user_info():
            Logger.trace(f"API request for path: {request.path}")
            try:
                token = request.headers.get('Authorization')
                if not token:
                    return {"message": "Missing parameters"}, HTTP.BAD_REQUEST
                
                access_token = self.database.get_user_token_by_token(token)
                if not access_token or not access_token.is_valid():
                    return {"message": "Invalid token"}, HTTP.UNAUTHORIZED
                
                user = self.database.get_user(access_token.username)
                return {
                    "username": user.username,
                    "access_level": user.access_level.name
                }, HTTP.OK
                
            except Exception as e:
                Logger.error(f"Error processing user info request: {e}")
                Logger.trace(f"Error details: {traceback.format_exc()}")
                return {"message": "Internal Server Error"}, HTTP.INTERNAL_SERVER_ERROR


###################################################################################################
# endregion: user
###################################################################################################
