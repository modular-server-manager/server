import multiprocessing as mp
import threading as th
import time
from datetime import datetime
from typing import Any, Dict

from gamuLogger import Levels, Logger
from version import Version

from mc_srv_manager.bus import Bus, BusData, Events
from mc_srv_manager.bus.bus_dispatcher import BusDispatcher
from mc_srv_manager.minecraft.forge.web_interface import WebInterface

# create a BusDispatcher, start it in a separate thread
# then create some Bus instances, each one in a separate process

Logger.show_threads_name()
Logger.show_pid()
Logger.set_level("stdout", Levels.DEBUG)
Logger.set_module("Bus.Test")


def bus_process1(bus_data : BusData):
    Logger.info("Starting bus_process1")
    bus = Bus(bus_data)
    bus.start()
    #bus.trigger(Events["SERVER.START"], server_name="TestServer", timestamp=int(datetime.now().timestamp()))
    time.sleep(2)
    print(bus.trigger(Events["GET_VERSIONS.MINECRAFT"]))
    time.sleep(1)
    bus.stop()

def bus_process2(bus_data : BusData):
    Logger.info("Starting bus_process2")
    bus = Bus(bus_data)
    def c(timestamp: datetime) -> list[Version]:
        return WebInterface.get_mc_versions().keys()
    def d(timestamp: datetime, mc_version: Version) -> Dict[Version, Dict[str, Any]]:
        return WebInterface.get_forge_versions(Version.from_string(mc_version))
    bus.register(Events["GET_VERSIONS.MINECRAFT"], c)
    bus.register(Events["GET_VERSIONS.FORGE"], d)
    bus.start()
    time.sleep(5)
    # bus.trigger(Events["SERVER.STARTING"], server_name="TestServer", timestamp=int(datetime.now().timestamp()))
    time.sleep(5)
    # bus.trigger(Events["SERVER.STARTED"], server_name="TestServer", timestamp=int(datetime.now().timestamp()))
    bus.stop()

def bus_thread(bus_data : BusData):
    Logger.info("Starting bus_thread")
    bus = Bus(bus_data)
    bus.start()
    time.sleep(12)
    bus.stop()

def main():
    # Create a BusDispatcher
    dispatcher = BusDispatcher(memory_size=8, max_string_length=8192)

    dispatcher_thread = th.Thread(target=dispatcher.mainloop, daemon=True, name="BusDispatcherThread")
    dispatcher_thread.start()

    # Get shared memory for the bus
    bus_data1 = dispatcher.get_bus_data("bus1")
    bus_data2 = dispatcher.get_bus_data("bus2")
    bus_data3 = dispatcher.get_bus_data("bus3")

    # Start the bus processes
    bus_process1_process = mp.Process(target=bus_process1, args=(bus_data1, ))
    bus_process2_process = mp.Process(target=bus_process2, args=(bus_data2, ))
    bus_thread_process = th.Thread(target=bus_thread, args=(bus_data3, ), daemon=True, name="BusThread")
    bus_process1_process.start()
    bus_process2_process.start()
    bus_thread_process.start()


    # Wait for the bus processes to finish
    bus_process1_process.join()
    bus_process2_process.join()
    bus_thread_process.join()


if __name__ == "__main__":
    main()
