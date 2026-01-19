from multiprocessing import shared_memory as shm
from multiprocessing import synchronize as sync

from .events import GROUP_SEPARATOR

class BusData:
    """
    Class to hold the shared memory data for the bus.
    """
    def __init__(self, write_list: shm.ShareableList, read_list: shm.ShareableList,
                 write_list_lock: sync.Lock, read_list_lock: sync.Lock, _for: str,
                 memory_size: int, max_string_length: int, name: str, id : int):
        self.write_list = write_list
        self.read_list = read_list
        self.write_list_lock = write_list_lock
        self.read_list_lock = read_list_lock
        self.memory_size = memory_size
        self.max_string_length = max_string_length
        self.empty_string = ' ' * max_string_length  # Define an empty string of max length
        self.name = name
        self.id = id
        self._for = _for


class BusMessagePrefix:
    """
    Class to hold the prefix for bus messages.
    """
    def __init__(self, source_id: int, target_id: int, fragment_number: int, fragment_count: int, message_id: int):
        self.source_id = source_id
        self.target_id = target_id
        self.fragment_number = fragment_number
        self.fragment_count = fragment_count
        self.message_id = message_id

    def __str__(self) -> str:
        return GROUP_SEPARATOR.join([
            f"{self.source_id:02X}",         # source_id
            f"{self.target_id:02X}",         # target_id
            f"{self.fragment_number:02X}",   # fragment number
            f"{self.fragment_count:02X}",    # total fragments count
            f"{self.message_id:02X}"         # message_id
        ])
        
    @staticmethod
    def length() -> int:
        """
        Returns the length of the bus message prefix.
        :return: Length of the prefix in bytes.
        """
        return 5 * 2 + 4 + 1  # 5 fields, each 2 hex digits + 4 separators (GROUP_SEPARATOR) + 1 for the final separator
        
    def __repr__(self) -> str:
        return (f"BusMessagePrefix(source_id={self.source_id}, target_id={self.target_id}, "
                f"fragment_number={self.fragment_number}, fragment_count={self.fragment_count}, "
                f"message_id={self.message_id})")
        
    @classmethod
    def from_string(cls, encoded: str) -> 'BusMessagePrefix':
        """
        Parses a string to create a BusMessagePrefix instance.
        :param encoded: The encoded string containing the prefix.
        :return: An instance of BusMessagePrefix.
        """
        parts = encoded.split(GROUP_SEPARATOR)
        if len(parts) != 5:
            raise ValueError("Encoded string does not have the expected prefix format.")
        
        source_id =         int(parts[0], 16)
        target_id =         int(parts[1], 16)
        fragment_number =   int(parts[2], 16)
        fragment_count =    int(parts[3], 16)
        message_id =        int(parts[4], 16)

        return cls(source_id, target_id, fragment_number, fragment_count, message_id)