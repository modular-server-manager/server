import argparse

from gamuLogger import config_argparse, config_logger

from .server.server import Server

BASE_PATH = __file__[:__file__.rfind('/')]  # get the base path of the server


def parse_args():
    parser = argparse.ArgumentParser(description="Start the HTTP server.")

    config_argparse(parser)

    parser.add_argument("-p", "--port", type=int, default=5000,
                        help="Port to run the server on (default: 5000)")
    parser.add_argument("-c", "--config", type=str, default=f"{BASE_PATH}/config.json")

    return parser.parse_args()

def main():
    args = parse_args()
    config_logger(args)
    server = Server(config_path=args.config, port=args.port)
    server.start()

if __name__ == "__main__":
    main()
