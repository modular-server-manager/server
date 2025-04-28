from gamuLogger import Logger
import re

Logger.set_module("version")
class Version:
    """
    Class to represent the version of the software.
    """

    def __init__(self, *args: int):
        """
        Initialize the Version object.
        
        :param args: Version elements (major, minor, patch, etc.)
        """
        if not args:
            raise ValueError("Version must be initialized with at least one argument.")

        self.__elements = args

    @classmethod
    def from_string(cls, version_str: str):
        """
        Create a Version object from a version string.

        :param version_str: Version string
        :return: Version object
        """
        Logger.trace(f"Creating Version object from string: {version_str}")
        parts = version_str.split('.')
        
        elements = map(int, parts)
        return cls(*elements)

    def __str__(self) -> str:
        """
        Return the version as a string.

        :return: Version string
        """
        return '.'.join(map(str, (self.__elements)))
    
    def __repr__(self) -> str:
        """
        Return a string representation of the Version object.

        :return: String representation
        """
        return "Version(" + ", ".join(map(str, self.__elements)) + ")"
    
    def __prepare_comparison(self, other : 'Version') -> tuple[tuple[int, ...], tuple[int, ...]]:
        """
        Prepare the version for comparison by ensuring both versions have the same number of elements.
        :param other: Another Version object
        :return: Tuple of (self, other) with padded elements
        """
        max_len = max(len(self.__elements), len(other.__elements))
        self_elements = self.__elements + (0,) * (max_len - len(self.__elements))
        other_elements = other.__elements + (0,) * (max_len - len(other.__elements))
        return self_elements, other_elements
    
    def __eq__(self, other) -> bool:
        """
        Check if two Version objects are equal (1.2.4 is considered equal to 1.2.4.0)
        :param other: Another Version object
        :return: True if equal, False otherwise
        """
        if not isinstance(other, Version):
            return NotImplemented
        self_elements, other_elements = self.__prepare_comparison(other)
        return self_elements == other_elements
    
    def __lt__(self, other) -> bool:
        """
        Check if this Version object is less than another
        :param other: Another Version object
        :return: True if this version is less, False otherwise
        """
        if not isinstance(other, Version):
            return NotImplemented
        self_elements, other_elements = self.__prepare_comparison(other)
        return self_elements < other_elements
    
    def __le__(self, other) -> bool:
        """
        Check if this Version object is less than or equal to another.
        :param other: Another Version object
        :return: True if this version is less than or equal, False otherwise
        """
        if not isinstance(other, Version):
            return NotImplemented
        self_elements, other_elements = self.__prepare_comparison(other)
        return self_elements <= other_elements
    
    def __gt__(self, other) -> bool:
        """
        Check if this Version object is greater than another.
        :param other: Another Version object
        :return: True if this version is greater, False otherwise
        """
        if not isinstance(other, Version):
            return NotImplemented
        self_elements, other_elements = self.__prepare_comparison(other)
        return self_elements > other_elements
    
    def __ge__(self, other) -> bool:
        """
        Check if this Version object is greater than or equal to another.
        :param other: Another Version object
        :return: True if this version is greater than or equal, False otherwise
        """
        if not isinstance(other, Version):
            return NotImplemented
        self_elements, other_elements = self.__prepare_comparison(other)
        return self_elements >= other_elements
    
    def __ne__(self, other) -> bool:
        """
        Check if two Version objects are not equal.
        :param other: Another Version object
        :return: True if not equal, False otherwise
        """
        if not isinstance(other, Version):
            return NotImplemented
        self_elements, other_elements = self.__prepare_comparison(other)
        return self_elements != other_elements
        
    def to_tuple(self) -> tuple[int, ...]:
        """
        Convert the version to a tuple.
        :return: Tuple of version elements
        """
        return self.__elements
    
    def __hash__(self):
        """
        Return a hash of the version.
        :return: Hash value
        """
        return hash(self.__elements)