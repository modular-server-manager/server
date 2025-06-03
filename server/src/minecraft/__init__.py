from typing import Callable, Dict, Type

from .Base_mc_server import BaseMcServer
from .forge.installer import install as install_forge
from .forge.server import ForgeServer
from .forge.web_interface import WebInterface
from .vanilla.server import MinecraftServer

McServersModules : Dict[str, Type[BaseMcServer]] = {
    "vanilla": MinecraftServer,
    "forge": ForgeServer
}

McInstallersModules : Dict[str, Callable[[], None]] = {
    "forge": install_forge
}
