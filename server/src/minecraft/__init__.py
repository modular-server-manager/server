from typing import Callable, Dict, Type

from version import Version

from .Base_mc_server import BaseMcServer, ServerStatus
from .forge.installer import install as install_forge
from .forge.server import ForgeServer
from .vanilla.installer import install as install_vanilla
from .vanilla.server import MinecraftServer
from .web_interface import WebInterface

McServersModules : Dict[str, Type[BaseMcServer]] = {
    "vanilla": MinecraftServer,
    "forge": ForgeServer
}

McInstallersModules : Dict[str, Callable[[str, str, Version], None]] = {
    "forge": install_forge,
    "vanilla": install_vanilla
}
