import time
from multiprocessing import Lock
from multiprocessing import shared_memory as shm
from multiprocessing.managers import SharedMemoryManager
from random import randint
import traceback

from gamuLogger import Logger

from .bus_data import BusData, BusMessagePrefix
from .events import FILE_SEPARATOR, EncodedEvent

type SharedMemories = tuple[shm.ShareableList, shm.ShareableList]

Logger.set_module("Bus.Dispatcher")

class BusDispatcher:
    def __init__(self, memory_size : int, max_string_length : int):
        if hasattr(self, "_BusDispatcher__shared_memories"):
            return
        self.__bus_datas: dict[str, BusData] = {}
        self.__ids: dict[str, int] = {}  # Store IDs for each key
        # this dispatcher is responsible for managing shared memories for different keys. only him can create and release them.
        self.__manager = SharedMemoryManager()
        self.__manager.start()

        self.__running = False

        self.__memory_size = memory_size
        self.__empty_string = ' ' * max_string_length  # Define an empty string of max length
        self.__max_string_length = max_string_length

    def __del__(self):
        self.__manager.shutdown()
        for key, bus_data in self.__bus_datas.items():
            bus_data.write_list.shm.close()
            bus_data.read_list.shm.close()
            try:
                bus_data.write_list.shm.unlink()
                bus_data.read_list.shm.unlink()
            except FileNotFoundError:
                pass

    def release_shared_memory(self, _for: str):
        """
        Release the shared memory for the given key.
        """
        if _for not in self.__bus_datas:
            raise KeyError(f"No data found for {_for}")
        bus_data = self.__bus_datas.pop(_for)
        bus_data.write_list.shm.close()
        bus_data.read_list.shm.close()
        bus_data.write_list.shm.unlink()
        bus_data.read_list.shm.unlink()
        Logger.debug(f"Shared memory for {_for} released.")

    def release_all_shared_memories(self):
        """
        Release all shared memories.
        """
        for key in list(self.__bus_datas.keys()):
            self.release_shared_memory(key)
        Logger.debug("All shared memories released.")

    def get_bus_data(self, _for: str) -> BusData:
        """
        Get the bus data containing all shared memories.
        """

        write_mem = self.__manager.ShareableList(
            [self.__empty_string] * self.__memory_size
        )
        read_mem = self.__manager.ShareableList(
            [self.__empty_string] * self.__memory_size
        )

        if _for not in self.__ids:
            # Generate a random ID for the bus data
            self.__ids[_for] = randint(1, 255)

        bd =  BusData(
            write_list=write_mem,
            read_list=read_mem,
            write_list_lock=Lock(),
            read_list_lock=Lock(),
            _for=_for,
            memory_size=self.__memory_size,
            max_string_length=self.__max_string_length,
            name=_for,
            id= self.__ids[_for]
        )
        self.__bus_datas[_for] = bd
        return bd

    def __move_forward(self, key : str):
        """
        Move the messages in the shared memory forward.
        """
        bus_data = self.__bus_datas[key]
        write_list = bus_data.write_list
        with bus_data.write_list_lock:
            for i in range(len(write_list) - 1):
                write_list[i] = write_list[i + 1]
            write_list[-1] = self.__empty_string

    def __get_source_target(self, encoded: EncodedEvent) -> tuple[int, int]:
        """
        Extract the source and target IDs from the encoded string.
        """
        prefix_str, data = encoded.string().split(FILE_SEPARATOR, 1)
        
        prefix = BusMessagePrefix.from_string(prefix_str)

        return prefix.source_id, prefix.target_id

    def mainloop(self):
        # write in read_list, read in write_list
        self.__running = True
        while self.__running:
            for rec_key, rec_bus_data in self.__bus_datas.items():
                with rec_bus_data.write_list_lock:
                    msg = EncodedEvent(rec_bus_data.write_list[0])
                if msg.string() == self.__empty_string:
                    continue
                Logger.debug(f"Processing messages from {rec_key}: {msg}")
                try:
                    for key, bus_data in self.__bus_datas.items():
                        if key == rec_key: # Skip the same key
                            continue
                        _, target_id = self.__get_source_target(msg)
                        if target_id not in (0, self.__ids[key]):
                            Logger.debug(f"Message {msg} not for {key}, skipping.")
                            continue
                        Logger.debug(f"Forwarding message {msg} to {key}")
                        with bus_data.read_list_lock:
                            # Find the first empty slot in the read list
                            for i in range(len(bus_data.read_list)):
                                if bus_data.read_list[i] == self.__empty_string:
                                    bus_data.read_list[i] = msg.string()
                                    Logger.trace(f"Message {msg} forwarded to {key} at index {i}")
                                    Logger.trace(f"Current read list for {key}:\n{'\n'.join(str(EncodedEvent(s)) if s != self.__empty_string else 'EMPTY' for s in bus_data.read_list)}")
                                    break
                            else:
                                Logger.warning(f"No empty slot found in {key} to forward message {msg}")
                    self.__move_forward(rec_key)
                except Exception as e:
                    Logger.error(f"Error processing message {msg} from {rec_key}: {e}")
                    Logger.debug(traceback.format_exc())
            time.sleep(0.01)

    def stop(self):
        """
        Stop the main loop of the bus dispatcher.
        """
        self.__running = False
