import argparse
import sys
import traceback

from gamuLogger import Logger, config_argparse, config_logger

Logger.show_pid()
Logger.show_threads_name()


BASE_PATH = __file__[:__file__.rfind('/')]  # get the base path of the server



parser = argparse.ArgumentParser(description="Start the HTTP server.")
config_argparse(parser)
parser.add_argument("-c", "--config", type=str, default=f"{BASE_PATH}/config.json")
args = parser.parse_args()
config_logger(args)

from .core import Core  # must be imported after Logger is configured


def main():
    try:
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
