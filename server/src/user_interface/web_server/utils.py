import re

from gamuLogger import Logger

Logger.set_module("User Interface.Utils")

RE_MC_SERVER_NAME = re.compile(r"^[a-zA-Z0-9_]{1,16}$") # Matches Minecraft server names (1-16 characters, letters, numbers, underscores)

def str2bool(v : str) -> bool:
    """
    Convert a string to a boolean value.
    """
    if isinstance(v, bool):
        return v
    if v.lower() in {'yes', 'true', 't', '1'}:
        return True
    if v.lower() in {'no', 'false', 'f', '0'}:
        return False
    raise ValueError(f"Invalid boolean string: {v}")

class NoLog:
    def write(self, *_): pass
    def flush(self): pass

def guess_type(filename: str) -> str:
    """
    Guess the MIME type of a file based on its extension.
    """
    mimetypes = {
        'html': 'text/html',
        'css': 'text/css',
        'js': 'application/javascript',
        'json': 'application/json',
        'png': 'image/png',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'svg': 'image/svg+xml',
        'webp': 'image/webp',
        'woff': 'font/woff',
        'woff2': 'font/woff2',
        'ttf': 'font/ttf',
        'otf': 'font/otf'
    }
    ext = filename.split('.')[-1].lower()
    if ext not in mimetypes:
        Logger.warning(f"Unknown file extension: {ext}, defaulting to application/octet-stream")
        return 'application/octet-stream'
    return mimetypes[ext]