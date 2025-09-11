from typing import Dict

from .Base_interface import BaseInterface
from .tk_window import TkWindow
from .web_server import WebServer

UserInterfaceModules : Dict[str, type[BaseInterface]] = {
    "web": WebServer,
    "tk": TkWindow
}
