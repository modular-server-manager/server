import argparse
import sys
import traceback

from gamuLogger import Logger, config_argparse, config_logger

Logger.show_pid()
Logger.show_threads_name()

Logger.set_module("App.Main")


BASE_PATH = __file__[:__file__.rfind('/')]  # get the base path of the server


parser = argparse.ArgumentParser(description="Start the application.")
config_argparse(parser)
parser.add_argument("-c", "--config", type=str, default=f"{BASE_PATH}/config.json")
args = parser.parse_args()
config_logger(args)

from .core import \
    Core  # must be imported after config_logger to ensure logging is set up correctly

def format_platform() -> str:
    if sys.platform.startswith("linux"):
        try:
            import distro
            return f"{distro.name(pretty=True)}"
        except ImportError:
            return "Linux (distro module not installed)"
    elif sys.platform == "darwin":
        try:
            import platform
            mac_ver = platform.mac_ver()[0]
            return f"macOS {mac_ver}"
        except Exception:
            return "macOS (version unknown)"
    elif sys.platform == "win32":
        try:
            import platform
            win_ver = platform.win32_ver()
            return f"Windows {win_ver[0]} {win_ver[1]}"
        except Exception:
            return "Windows (version unknown)"
    else:
        return sys.platform

def format_java_info() -> str:
    import subprocess
    try:
        result = subprocess.run(["java", '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stderr.splitlines()[0]  # Java version info is usually in stderr
        else:
            return f"Error executing java: {result.stderr.strip()}"
    except FileNotFoundError:
        return "Java executable not found"
    except Exception as e:
        return f"Error retrieving Java version: {e}"

Logger.info(f"Python version: {sys.version}\nOperating System: {format_platform()}\nJava Info: {format_java_info()}")
Logger.debug(f"Starting application with arguments:\n{"\n".join(f"{k}: {v}" for k, v in args.__dict__.items())}")

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
