from .server import HttpServer
import argparse
from gamuLogger import Logger, Levels
from gamuLogger.custom_types import COLORS


def parse_args():
    parser = argparse.ArgumentParser(description="Start the HTTP server.")
    
    logging_group = parser.add_argument_group("Logging options")
    
    logging_group.add_argument("-d", "--debug", type=str, metavar="LEVEL",
        choices=["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "FATAL"], default="INFO", nargs="?", const="DEBUG",
        help="Set the logging level for the console (default: INFO if not specified, DEBUG if used without value). Possible values are: FATAL, ERROR, WARNING, INFO, DEBUG, TRACE")
    
    logging_group.add_argument("--log-file", type=str, action="append", default=[], metavar="FILE:LEVEL",
        help="Add a log file, with the format <file_path>:<level>. The level can be one of the following: FATAL, ERROR, WARNING, INFO, DEBUG, TRACE. Can be used multiple times.")


    parser.add_argument("-p", "--port", type=int, default=5000,
                        help="Port to run the server on (default: 5000)")
    return parser.parse_args()

def set_log_level(args):
    level = Levels.from_string(args.debug)
    Logger.set_level("stdout", level)
    
def set_log_files(args):
    for log_file in args.log_file:
        file_path, level = log_file.split(":")
        print(file_path)
        level = Levels.from_string(level)
        Logger.add_target(file_path, level)



def main():
    args = parse_args()
    set_log_level(args)
    set_log_files(args)
    server = HttpServer(port=args.port)
    server.start()

if __name__ == "__main__":
    main()