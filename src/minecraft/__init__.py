from typing import Callable, Dict, Type

from version import Version

from .Base_mc_server import BaseMcServer, ServerStatus
from .forge.installer import install as install_forge
from .forge.server import ForgeServer
from .vanilla.installer import install as install_vanilla
from .vanilla.server import MinecraftServer
# from .fabric.installer import install as install_fabric
# from .fabric.server import FabricServer

from .web_interface import WebInterface

McServersModules : Dict[str, Type[BaseMcServer]] = {
    "vanilla": MinecraftServer,
    "forge": ForgeServer
    # "fabric": FabricServer
}

McInstallersModules : Dict[str, Callable[[str, str, Version], None]] = {
    "forge": install_forge,
    "vanilla": install_vanilla,
    # "fabric": install_fabric
}

McInstallersUrls : Dict[str, Callable[[Version, Version], str]] = {
    "forge": WebInterface.get_forge_installer_url,
    "vanilla": WebInterface.get_mc_installer_url,
    "fabric": WebInterface.get_fabric_installer_url
}