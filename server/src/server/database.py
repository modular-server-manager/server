import sqlite3
from enum import Enum
import os

from gamuLogger import Logger

from ..utils.version import Version

Logger.set_module("database")

class AccessLevel(Enum):
    USER = 0        # Global : Nothing              McServer : Can see server status
    ADMIN = 1       # Global : Nothing              McServer : Can start/stop servers, see logs, manage settings
    OPERATOR = 2    # Global : Can manage users     McServer : Can create and delete servers

class ServerStatus(Enum):
    STOPPED = 0
    STARTING = 1
    RUNNING = 2
    STOPPING = 3
    ERROR = 4

class User:
    def __init__(self, username: str, password: str, access_level: AccessLevel = AccessLevel.USER):
        self.username = username
        self.password = password
        self.access_level = access_level

    def __repr__(self):
        return f"User(username={self.username}, access_level={self.access_level})"

class McServer:
    def __init__(self, name: str, mc_version: Version, forge_version: Version, path : str, status: ServerStatus = ServerStatus.STOPPED):
        self.name = name
        self.mc_version = mc_version
        self.forge_version = forge_version
        self.path = path
        self.status = status

    def __repr__(self):
        return f"McServer(name={self.name}, mc_version={self.mc_version}, forge_version={self.forge_version}, status={self.status})"


class Database:
    def __init__(self, db_file):
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        try:
            self.connection = sqlite3.connect(db_file)
        except sqlite3.Error as e:
            Logger.error(f"Error connecting to database: {e}")
            Logger.debug(f"Database file: {db_file}")
            raise e
        self.cursor = self.connection.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                global_access_level INTEGER NOT NULL DEFAULT 0
            );
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS servers (
                name TEXT PRIMARY KEY,
                mc_version TEXT NOT NULL,
                forge_version TEXT NOT NULL,
                status INTEGER NOT NULL DEFAULT 0,
                path TEXT NOT NULL
            );
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS server_users_access (
                server_name TEXT NOT NULL,
                user_name TEXT NOT NULL,
                access_level INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (server_name) REFERENCES servers (name),
                FOREIGN KEY (user_name) REFERENCES users (username),
                PRIMARY KEY (server_name, user_name)
            );
        ''')
        self.connection.commit()

    def add_user(self, user : User):
        """
        Add a new user to the database.
        """
        self.cursor.execute('''
            INSERT INTO users (username, password, access_level)
            VALUES (?, ?, ?)
        ''', (user.username, user.password, user.access_level.value))
        self.connection.commit()
        
        # set default access level for all servers
        for server in self.get_servers():
            self.set_user_access(server.name, user.username, AccessLevel.USER)
        Logger.debug(f"User {user.username} added with access level {user.access_level.name}")

    def get_user(self, username : str) -> User:
        """
        Get a user from the database.
        :param username: The username of the user.
        :return: The user object.
        """
        self.cursor.execute('''
            SELECT * FROM users WHERE username = ?
        ''', (username,))
        res = self.cursor.fetchone()
        if res is None:
            raise ValueError(f"User {username} not found")
        return User(
            username=res[1],
            password=res[2],
            access_level=AccessLevel(res[3])
        )

    def has_user(self, username : str) -> bool:
        """
        Check if a user exists in the database.
        :param username: The username of the user.
        :return: True if the user exists, False otherwise.
        """
        self.cursor.execute('''
            SELECT * FROM users WHERE username = ?
        ''', (username,))
        return self.cursor.fetchone() is not None

    def update_user(self, user : User):
        """
        Update a user in the database.
        :param user: The user object.
        """
        self.cursor.execute('''
            UPDATE users SET password = ?, access_level = ?
            WHERE username = ?
        ''', (user.password, user.access_level.value, user.username))
        self.connection.commit()
        Logger.debug(f"User {user.username} updated with access level {user.access_level.name}")

    def delete_user(self, username : str):
        """
        Delete a user from the database.
        :param username: The username of the user.
        """
        self.cursor.execute('''
            DELETE FROM users WHERE username = ?
        ''', (username,))
        self.connection.commit()
        
        # delete all access levels for this user
        self.cursor.execute('''
            DELETE FROM server_users_access WHERE user_name = ?
        ''', (username,))
        self.connection.commit()

    def get_users(self) -> list[User]:
        """
        Get all users from the database.
        :return: A list of user objects.
        """
        self.cursor.execute('''
            SELECT * FROM users
        ''')
        res = self.cursor.fetchall()
        if res is None:
            raise ValueError("No users found")
        return [User(
            username=row[1],
            password=row[2],
            access_level=AccessLevel(row[3])
        ) for row in res]


    def add_server(self, server : McServer):
        """
        Add a new server to the database.
        :param server: The server object.
        """
        self.cursor.execute('''
            INSERT INTO servers (name, mc_version, forge_version, status, path)
            VALUES (?, ?, ?, ?, ?)
        ''', (server.name, str(server.mc_version), str(server.forge_version), server.status.value, server.path))
        self.connection.commit()
        
        # set default access level for all users
        for user in self.get_users():
            self.set_user_access(server.name, user.username, AccessLevel.USER)
        Logger.debug(f"McServer {server.name} version {server.mc_version}-{server.forge_version} added with status {server.status.name}")
        
    def get_server(self, name : str) -> McServer:
        """
        Get a server from the database.
        :param name: The name of the server.
        :return: The server object.
        """       
        self.cursor.execute('''
            SELECT * FROM servers WHERE name = ?
        ''', (name,))
        res = self.cursor.fetchone()
        if res is None:
            raise ValueError(f"McServer {name} not found")
        return McServer(
            name=res[1],
            mc_version=Version.from_string(res[2]),
            forge_version=Version.from_string(res[3]),
            status=ServerStatus(res[4]),
            path=res[5]
        )
        
    def has_server(self, name : str) -> bool:
        """
        Check if a server exists in the database.
        :param name: The name of the server.
        :return: True if the server exists, False otherwise.
        """
        self.cursor.execute('''
            SELECT * FROM servers WHERE name = ?
        ''', (name,))
        return self.cursor.fetchone() is not None
    
    def update_server(self, server : McServer):
        """
        Update a server in the database.
        :param server: The server object.
        """
        self.cursor.execute('''
            UPDATE servers SET mc_version = ?, forge_version = ?, status = ?, path = ?
            WHERE name = ?
        ''', (str(server.mc_version), str(server.forge_version), server.status.value, server.path, server.name))
        self.connection.commit()
        
    def delete_server(self, name : str):
        """
        Delete a server from the database.
        :param name: The name of the server.
        """
        self.cursor.execute('''
            DELETE FROM servers WHERE name = ?
        ''', (name,))
        self.connection.commit()
        
        # delete all access levels for this server
        self.cursor.execute('''
            DELETE FROM server_users_access WHERE server_name = ?
        ''', (name,))
        self.connection.commit()

    def get_servers(self) -> list[McServer]:
        """
        Get all servers from the database.
        :return: A list of server objects.
        """
        self.cursor.execute('''
            SELECT * FROM servers
        ''')
        res = self.cursor.fetchall()
        if res is None:
            raise ValueError("No servers found")
        return [McServer(
            name=row[1],
            mc_version=Version.from_string(row[2]),
            forge_version=Version.from_string(row[3]),
            status=ServerStatus(row[4]),
            path=row[5]
        ) for row in res]

    def set_user_access(self, server_name : str, user_name : str, access_level : AccessLevel):
        """
        Set the access level of a user for a specific server.
        :param server_name: The name of the server.
        :param user_name: The username of the user.
        :param access_level: The access level of the user.
        """
        self.cursor.execute('''
            INSERT OR REPLACE INTO server_users_access (server_name, user_name, access_level)
            VALUES (?, ?, ?)
        ''', (server_name, user_name, access_level.value))
        self.connection.commit()
