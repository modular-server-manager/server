from .server import HttpServer
import argparse
from gamuLogger import Logger, Levels
from gamuLogger.custom_types import COLORS


def parse_args():
    parser = argparse.ArgumentParser(description="Start the HTTP server.")
    #take a number between FATAL (0) and TRACE (5) (usage : -d 2 or -d (will set to 4))
    parser.add_argument("-d", "--debug", type=int, choices=range(6), default=3,
                        metavar="LEVEL", nargs="?", const=4,
                        help="Set the debug level (0-5, default: 3 if not specified, 4 if used without number)")
    
    parser.add_argument("-p", "--port", type=int, default=5000,
                        help="Port to run the server on (default: 5000)")
    return parser.parse_args()

def set_log_level(args):
    if args.debug == 0:
        level = Levels.FATAL
    elif args.debug == 1:
        level = Levels.ERROR
    elif args.debug == 2:
        level = Levels.WARNING
    elif args.debug == 3:
        level = Levels.INFO
    elif args.debug == 4:
        level = Levels.DEBUG
    elif args.debug == 5:
        level = Levels.TRACE
    
    Logger.set_level("stdout", level)



def main():
    args = parse_args()
    set_log_level(args)
    server = HttpServer(port=args.port)
    server.start()

if __name__ == "__main__":
    main()