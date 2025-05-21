import argparse
import os

from config import JSONConfig
from gamuLogger import Logger, config_argparse, config_logger

from .database.types import ServerStatus
from .minecraft.forge.server import ForgeServer
from .utils.debug_tk import DebugTk, ask_for_choice

Logger.set_module("forge server.debug interface")

BASE_PATH = __file__[:__file__.rfind('/')]  # get the base path of the server


def parse_args():
    parser = argparse.ArgumentParser(description="Start the HTTP server.")

    config_argparse(parser)

    parser.add_argument("-c", "--config", type=str, default=f"{BASE_PATH}/config.json")

    return parser.parse_args()

def main():
    args = parse_args()
    config_logger(args)

    conf = JSONConfig(args.config)
    srvs_path = conf.get("forge_servers_path")
    srv_path = ask_for_choice("Select a server", "Choose the path of the server to start", os.listdir(srvs_path))

    root = DebugTk()

    server = ForgeServer(
        installation_dir=os.path.join(srvs_path, srv_path),
        on_stop=root.close
    )


    class SendCmd:
        def __init__(self):
            self.send = server.send_command
            self.write_res = None

        def __call__(self, cmd: str):
            if res := self.send(cmd):
                self.write_res(res)

    send_cmd = SendCmd()


    write_term, clear_term = root.add_terminal(send_cmd)
    send_cmd.write_res = write_term


    root.add_button("Stop Server", server.stop)
    root.add_button("Reload World", server.reload_world)
    root.add_button("Get Player List", lambda: Logger.info(server.get_player_list()))
    root.add_button("Get Seed", lambda: Logger.info(server.get_seed()))

    server.start()

    server.set_on_chat_message(write_term) # only set this after the server is started to avoid adding messages before the window is created

    if server.get_status() != ServerStatus.RUNNING:
        Logger.fatal("Server is not running")
        root.close()
        return

    root.mainloop()


if __name__ == "__main__":
    main()
