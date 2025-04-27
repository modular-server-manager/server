class Version:
    """
    Class to represent the version of the software.
    """

    def __init__(self, major: int, minor: int, patch: int):
        """
        Initialize the Version object with major, minor, and patch numbers.

        :param major: Major version number
        :param minor: Minor version number
        :param patch: Patch version number
        """
        self.major = major
        self.minor = minor
        self.patch = patch

    @classmethod
    def from_string(cls, version_str: str):
        """
        Create a Version object from a version string.

        :param version_str: Version string in the format 'major.minor.patch'
        :return: Version object
        """
        parts = version_str.split('.')
        if len(parts) != 3:
            raise ValueError("Version string must be in the format 'major.minor.patch'")
        
        major, minor, patch = map(int, parts)
        return cls(major, minor, patch)

    def __str__(self) -> str:
        """
        Return the version as a string in the format 'major.minor.patch'.

        :return: Version string
        """
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def __repr__(self) -> str:
        """
        Return a string representation of the Version object.

        :return: String representation
        """
        return f"Version(major={self.major}, minor={self.minor}, patch={self.patch})"
    
    def __eq__(self, other) -> bool:
        """
        Check if two Version objects are equal.
        :param other: Another Version object
        :return: True if equal, False otherwise
        """
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)
    
    def __lt__(self, other) -> bool:
        """
        Check if this Version object is less than another.
        :param other: Another Version object
        :return: True if this version is less, False otherwise
        """
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
    
    def __le__(self, other) -> bool:
        """
        Check if this Version object is less than or equal to another.
        :param other: Another Version object
        :return: True if this version is less than or equal, False otherwise
        """
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)
    
    def __gt__(self, other) -> bool:
        """
        Check if this Version object is greater than another.
        :param other: Another Version object
        :return: True if this version is greater, False otherwise
        """
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)
    
    def __ge__(self, other) -> bool:
        """
        Check if this Version object is greater than or equal to another.
        :param other: Another Version object
        :return: True if this version is greater than or equal, False otherwise
        """
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) >= (other.major, other.minor, other.patch)
    
    def __ne__(self, other) -> bool:
        """
        Check if two Version objects are not equal.
        :param other: Another Version object
        :return: True if not equal, False otherwise
        """
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch)
        
    def to_tuple(self) -> tuple[int, int, int]:
        """
        Convert the version to a tuple.
        :return: Tuple of (major, minor, patch)
        """
        return (self.major, self.minor, self.patch)
    
    def __hash__(self):
        """
        Return a hash of the version.
        :return: Hash value
        """
        return hash((self.major, self.minor, self.patch))