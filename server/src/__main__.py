import argparse
import sys
import traceback

from gamuLogger import Logger, config_argparse, config_logger

Logger.show_pid()
Logger.show_threads_name()

from .core import Core

BASE_PATH = __file__[:__file__.rfind('/')]  # get the base path of the server


def parse_args():
    parser = argparse.ArgumentParser(description="Start the HTTP server.")

    config_argparse(parser)

    parser.add_argument("-c", "--config", type=str, default=f"{BASE_PATH}/config.json")

    return parser.parse_args()

def main():
    try:
        args = parse_args()
        config_logger(args)
        core = Core(args.config)
        core.start()
        core.mainloop()
    except Exception as e:
        Logger.fatal(f"An error occurred: {e}")
        Logger.debug(traceback.format_exc())
        return 1
    else:
        return 0

if __name__ == "__main__":
    sys.exit(main())
