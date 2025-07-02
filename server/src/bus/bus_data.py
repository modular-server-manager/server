from multiprocessing import shared_memory as shm
from multiprocessing import synchronize as sync


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
