import os
import sqlite3
from datetime import datetime
from typing import Dict

from gamuLogger import Logger

from .types import AccessLevel, AccessToken, User

Logger.set_module("database")

class Database:
    __instances : Dict[str, 'Database'] = {}

    def __new__(cls, db_file: str):
        """
        Singleton pattern to ensure only one instance of the database exists.
        :param db_file: The path to the database file.
        :return: The instance of the database.
        """
        if db_file not in cls.__instances:
            cls.__instances[db_file] = super(Database, cls).__new__(cls)
        return cls.__instances[db_file]

    def __init__(self, db_file : str):
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
                access_level INTEGER NOT NULL DEFAULT 0,
                registered_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
                last_login INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
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
            INSERT INTO users (username, password, access_level, registered_at, last_login)
            VALUES (?, ?, ?, ?, ?)
        ''',
            (
                user.username,
                user.password,
                user.access_level.value,
                int(datetime.now().timestamp()),
                int(datetime.now().timestamp())
            )
        )
        self.connection.commit()

        # set default access level for all servers
        Logger.debug(f"User {user.username} added with access level {user.access_level.name}")

    def get_user(self, username : str) -> User:
        """
        Get a user from the database.
        :param username: The username of the user.
        :return: The user object.
        """
        self.cursor.execute('''
            SELECT username, password, access_level, registered_at, last_login
            FROM users WHERE username = ?
        ''', (username,))
        res = self.cursor.fetchone()
        if res is None:
            raise ValueError(f"User {username} not found")
        Logger.trace(res)
        return User(
            username=res[0],
            password=res[1],
            access_level=AccessLevel(res[2]),
            registered_at=datetime.fromtimestamp(res[3]),
            last_login=datetime.fromtimestamp(res[4])
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
            UPDATE users SET password = ?, access_level = ?, last_login = ?
            WHERE username = ?
        ''', (user.password, user.access_level.value, int(user.last_login.timestamp()), user.username))
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
            access_level=AccessLevel(row[3]),
            registered_at=datetime.fromtimestamp(row[4]),
            last_login=datetime.fromtimestamp(row[5])
        ) for row in res]


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
