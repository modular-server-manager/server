import secrets
from datetime import datetime
from enum import IntEnum


class AccessLevel(IntEnum):
    USER = 0        # Global: Can see servers status
    ADMIN = 1       # Global: Can start/stop servers, see logs, manage settings
    OPERATOR = 2    # Global: Can manage users and create and delete servers


class User:
    def __init__(self, username: str, password: str, registered_at : datetime, last_login : datetime, access_level: AccessLevel = AccessLevel.USER):
        self.username = username
        self.password = password
        self.registered_at = registered_at
        self.last_login = last_login
        self.access_level = access_level

    def __repr__(self):
        return f"User(username={self.username}, access_level={self.access_level}, registered_at={self.registered_at.strftime("%d/%m/%Y, %H:%M:%S")}, last_login={self.last_login.strftime("%d/%m/%Y, %H:%M:%S")})"

    @classmethod
    def new(cls, username: str, password: str, access_level: AccessLevel = AccessLevel.USER):
        """
        Create a new user.
        :param username: The username of the user.
        :param password: The password of the user.
        :param access_level: The access level of the user.
        :return: The user object.
        """
        return cls(
            username,
            password,
            datetime.now(),
            datetime.now(),
            access_level
        )

class AccessToken:
    def __init__(self, username: str, token: str, expiration: datetime, remember: bool):
        self.username = username
        self.token = token
        self.expiration = expiration
        self.remember = remember

    def is_valid(self):
        """
        Check if the token is valid (not expired).
        :return: True if the token is valid, False otherwise.
        """
        return self.expiration > datetime.now()

    def __repr__(self):
        return f"AccessToken(username={self.username}, token={self.token}, expiration={self.expiration})"

    @classmethod
    def new(cls, username: str, expiration: datetime, remember: bool = False):
        """
        Create a new access token.
        :param username: The username of the user.
        :param expiration: The expiration time of the token.
        :param remember: Whether to remember the token or not.
        :return: The access token object.
        """
        token = secrets.token_urlsafe(64)
        return cls(username, token, expiration, remember)
