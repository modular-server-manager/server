import os
import sqlite3
from datetime import datetime

from gamuLogger import Logger
from version import Version

from .types import AccessLevel, AccessToken, McServer, ServerStatus, User

Logger.set_module("database")

class Database:
    def __init__(self, db_file):
        Logger.debug(f"Connecting to database {db_file}")
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        try:
            self.connection = sqlite3.connect(db_file)
        except sqlite3.Error as e:
            Logger.error(f"Error connecting to database: {e}")
            Logger.debug(f"Database file: {db_file}")
            raise e
        self.cursor = self.connection.cursor()
        self.create_table()
        Logger.info(f"Database connected to {db_file}")

    def close(self):
        """
        Close the database connection.
        """
        if self.connection:
            self.connection.close()
            Logger.debug("Database connection closed")
        else:
            Logger.debug("No database connection to close")

    def __del__(self):
        """
        Destructor to close the database connection when the object is deleted.
        """
        self.close()

    def create_table(self):
        # table users
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                global_access_level INTEGER NOT NULL DEFAULT 0,
                registered_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
                last_login INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
                last_ip TEXT NOT NULL
            );
        ''')
        # table servers
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS servers (
                name TEXT PRIMARY KEY,
                mc_version TEXT NOT NULL,
                forge_version TEXT NOT NULL,
                status INTEGER NOT NULL DEFAULT 0
            );
        ''')
        # table server_users_access
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
        # table access_tokens
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_tokens (
                username TEXT PRIMARY KEY,
                token TEXT NOT NULL,
                expiration INTEGER NOT NULL,
                remember BOOLEAN NOT NULL DEFAULT 0,
                FOREIGN KEY (username) REFERENCES users (username),
                UNIQUE (token)
            );
        ''')

        self.connection.commit()

    def add_user(self, user : User):
        """
        Add a new user to the database.
        """
        self.cursor.execute('''
            INSERT INTO users (username, password, global_access_level, registered_at, last_login, last_ip)
            VALUES (?, ?, ?, ?, ?, ?)
        ''',
            (
                user.username,
                user.password,
                user.global_access_level.value,
                int(datetime.now().timestamp()),
                int(datetime.now().timestamp()),
                user.last_ip
            )
        )
        self.connection.commit()

        # set default access level for all servers
        for server in self.get_servers():
            self.set_user_access(server.name, user.username, AccessLevel.USER)
        Logger.debug(f"User {user.username} added with access level {user.global_access_level.name}")

    def get_user(self, username : str) -> User:
        """
        Get a user from the database.
        :param username: The username of the user.
        :return: The user object.
        """
        self.cursor.execute('''
            SELECT username, password, global_access_level, registered_at, last_login, last_ip
            FROM users WHERE username = ?
        ''', (username,))
        res = self.cursor.fetchone()
        if res is None:
            raise ValueError(f"User {username} not found")
        Logger.trace(res)
        return User(
            username=res[0],
            password=res[1],
            global_access_level=AccessLevel(res[2]),
            registered_at=datetime.fromtimestamp(res[3]),
            last_login=datetime.fromtimestamp(res[4]),
            last_ip=res[5]
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
        Update a user (defined by it's username) in the database.
        :param user: The user object.
        """
        self.cursor.execute('''
            UPDATE users SET password = ?, global_access_level = ?, last_login = ?, last_ip = ?
            WHERE username = ?
        ''', (user.password, user.global_access_level.value, int(user.last_login.timestamp()), user.last_ip, user.username))
        self.connection.commit()
        Logger.debug(f"User {user} updated")

    def delete_user(self, username : str):
        """
        Delete a user from the database.
        :param username: The username of the user.
        """
        # delete user from users table
        self.cursor.execute('''
            DELETE FROM users WHERE username = ?
        ''', (username,))
        self.connection.commit()
        Logger.debug(f"User {username} deleted")

        # delete all access levels for this user
        self.cursor.execute('''
            DELETE FROM server_users_access WHERE user_name = ?
        ''', (username,))
        self.connection.commit()
        Logger.debug(f"Access levels for user {username} deleted")

        # delete all access tokens for this user
        self.cursor.execute('''
            DELETE FROM access_tokens WHERE username = ?
        ''', (username,))
        self.connection.commit()
        Logger.debug(f"Access tokens for user {username} deleted")

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
            global_access_level=AccessLevel(row[3]),
            registered_at=datetime.fromtimestamp(row[4]),
            last_login=datetime.fromtimestamp(row[5]),
            last_ip=row[6]
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
            name=row[0],
            mc_version=Version.from_string(row[1]),
            forge_version=Version.from_string(row[2]),
            status=ServerStatus(row[3])
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

    def get_user_access(self, server_name : str, user_name : str) -> AccessLevel:
        """
        Get the access level of a user for a specific server.
        :param server_name: The name of the server.
        :param user_name: The username of the user.
        :return: The access level of the user.
        """
        self.cursor.execute('''
            SELECT * FROM server_users_access WHERE server_name = ? AND user_name = ?
        ''', (server_name, user_name))
        res = self.cursor.fetchone()
        if res is None:
            raise ValueError(f"Access level for user {user_name} on server {server_name} not found")
        return AccessLevel(res[2])


    def set_user_token(self, access_token : AccessToken):
        """
        Set the access token for a user.
        :param username: The username of the user.
        :param token: The access token.
        :param expiration: The expiration time of the token.
        """
        self.cursor.execute('''
            INSERT OR REPLACE INTO access_tokens (username, token, expiration, remember)
            VALUES (?, ?, ?, ?)
        ''', (access_token.username, access_token.token, int(access_token.expiration.timestamp()), "TRUE" if access_token.remember else "FALSE"))
        self.connection.commit()
        Logger.debug(f"Access token for user {access_token.username} set to \"{access_token.token}\"\nwith expiration {access_token.expiration.strftime('%Y-%m-%d %H:%M:%S')} {'(remembered)' if access_token.remember else ''}")
        return self

    def get_user_token(self, username : str) -> AccessToken:
        """
        Get the access token for a user.
        :param username: The username of the user.
        :return: The access token.
        """
        self.cursor.execute('''
            SELECT * FROM access_tokens WHERE username = ?
        ''', (username,))
        res = self.cursor.fetchone()
        if res is None:
            raise ValueError(f"Access token for user {username} not found")
        return AccessToken(
            username=res[1],
            token=res[2],
            expiration=datetime.fromtimestamp(res[3]),
            remember=res[4] == "TRUE"
        )

    def get_user_token_by_token(self, token : str) -> AccessToken:
        """
        Get the access token for a user by token.
        :param token: The access token.
        :return: The access token object.
        """
        self.cursor.execute('''
            SELECT * FROM access_tokens WHERE token = ?
        ''', (token,))
        res = self.cursor.fetchone()
        if res is None:
            raise ValueError(f"Access token {token} not found")
        return AccessToken(
            username=res[0],
            token=res[1],
            expiration=datetime.fromtimestamp(res[2]),
            remember=res[3] == "TRUE"
        )

    def get_user_from_token(self, token : str) -> User:
        """
        Get the user from an access token.
        :param token: The access token.
        :return: The user object.
        """
        self.cursor.execute('''
            SELECT * FROM access_tokens WHERE token = ?
        ''', (token,))
        res = self.cursor.fetchone()
        if res is None:
            raise ValueError(f"Access token {token} not found")
        return self.get_user(res[0])

    def exist_user_token(self, token : str) -> bool:
        """
        Check if an access token exists in the database.
        :param token: The access token.
        :return: True if the token exists, False otherwise.
        """
        self.cursor.execute('''
            SELECT * FROM access_tokens WHERE token = ?
        ''', (token,))
        return self.cursor.fetchone() is not None

    def delete_user_token(self, token : str):
        """
        Delete the access token for a user.
        :param username: The username of the user.
        """
        self.cursor.execute('''
            DELETE FROM access_tokens WHERE token = ?
        ''', (token,))
        self.connection.commit()
        Logger.debug(f"Access token {token} deleted")
        return self
