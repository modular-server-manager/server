from abc import ABC, abstractmethod


class BaseMcServer(ABC):
    """
    Base class for Minecraft servers.
    This class is used to define the basic structure and functionality of a Minecraft server.
    """

    def __init__(self, config_path: str):
        ...
