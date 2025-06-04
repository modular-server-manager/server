import time
from multiprocessing import shared_memory as shm
from multiprocessing.managers import SharedMemoryManager

from gamuLogger import Logger
from singleton import Singleton

from .bus_data import BusData

type SharedMemories = tuple[shm.ShareableList, shm.ShareableList]

Logger.set_module("bus dispatcher")

class BusDispatcher(Singleton):
    def __init__(self, memory_size : int, max_string_length : int):
        if hasattr(self, "_BusDispatcher__shared_memories"):
            return
        self.__shared_memories: dict[str, SharedMemories] = {}
        # this dispatcher is responsible for managing shared memories for different keys. only him can create and release them.
        self.__manager = SharedMemoryManager()
        self.__manager.start()

        self.__running = False

        self.__memory_size = memory_size
        self.__empty_string = ' ' * max_string_length  # Define an empty string of max length
        self.__max_string_length = max_string_length

    def __del__(self):
        self.__manager.shutdown()
        for key, (write_list, read_list) in self.__shared_memories.items():
            write_list.shm.close()
            read_list.shm.close()
            write_list.shm.unlink()
            read_list.shm.unlink()

    def get_shared_memory(self, _for : str) -> SharedMemories:
        """
        Get a pair of shared memories (write and read) for the bus.
        the first one is for writing messages to the bus,
        the second one is for reading messages from the bus.
        """
        shared_list_write = self.__manager.ShareableList(
            [self.__empty_string] * self.__memory_size
        )
        shared_list_read = self.__manager.ShareableList(
            [self.__empty_string] * self.__memory_size
        )
        self.__shared_memories[_for] = (shared_list_write, shared_list_read)
        return shared_list_write, shared_list_read

    def release_shared_memory(self, _for: str):
        """
        Release the shared memory for the given key.
        """
        if _for not in self.__shared_memories:
            raise KeyError(f"No shared memory found for {_for}")
        write_list, read_list = self.__shared_memories.pop(_for)
        write_list.shm.close()
        read_list.shm.close()
        write_list.shm.unlink()
        read_list.shm.unlink()
        Logger.debug(f"Shared memory for {_for} released.")

    def release_all_shared_memories(self):
        """
        Release all shared memories.
        """
        for key in list(self.__shared_memories.keys()):
            self.release_shared_memory(key)
        Logger.debug("All shared memories released.")

    def get_bus_data(self, _for: str) -> BusData:
        """
        Get the bus data containing all shared memories.
        """
        write_mem, read_mem = self.get_shared_memory(_for)
        return BusData(
            write_list=write_mem,
            read_list=read_mem,
            memory_size=self.__memory_size,
            max_string_length=self.__max_string_length
        )

    def __move_forward(self, key : str):
        """
        Move the messages in the shared memory forward.
        """
        write_list, _ = self.__shared_memories[key]
        for i in range(len(write_list) - 1):
            write_list[i] = write_list[i + 1]
        write_list[-1] = self.__empty_string

    def mainloop(self):
        # write in read_list, read in write_list
        self.__running = True
        while self.__running:
            for rec_key, (write_list, _) in self.__shared_memories.items():
                msg = write_list[0]
                if msg == self.__empty_string:
                    continue
                Logger.debug(f"Processing messages from {rec_key}: {msg}")
                for key, (_, read_list) in self.__shared_memories.items():
                    if key == rec_key:
                        continue
                    Logger.debug(f"Forwarding message {msg} to {key}")
                    for i in range(len(read_list)):
                        if read_list[i] == self.__empty_string:
                            read_list[i] = msg
                            Logger.trace(f"Message {msg} forwarded to {key} at index {i}")
                            break
                    else:
                        Logger.warning(f"No empty slot found in {key} to forward message {msg}")
                self.__move_forward(rec_key)
            time.sleep(0.01)

    def stop(self):
        """
        Stop the main loop of the bus dispatcher.
        """
        self.__running = False
