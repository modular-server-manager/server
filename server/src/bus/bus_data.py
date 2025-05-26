from multiprocessing import shared_memory as shm


class BusData:
    """
    Class to hold the shared memory data for the bus.
    """
    def __init__(self, write_list: shm.ShareableList, read_list: shm.ShareableList,
                 memory_size: int, max_string_length: int):
        self.write_list = write_list
        self.read_list = read_list
        self.memory_size = memory_size
        self.max_string_length = max_string_length
        self.empty_string = ' ' * max_string_length  # Define an empty string of max length
