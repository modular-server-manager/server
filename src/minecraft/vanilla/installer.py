import os
import secrets
import subprocess

from gamuLogger import Logger
from version import Version

from ..properties import Properties

Logger.set_module("Mc Server.Mc Installer")


EULA="""#By changing the setting below to TRUE you are indicating your agreement to our EULA (https://aka.ms/MinecraftEULA).
eula=true
"""


def set_eula(installation_dir : str) -> None:
    """
    Patch the EULA file to accept the Minecraft EULA.

    :param installation_dir: Directory where the server is installed.
    """

    eula_path = f"{installation_dir}/eula.txt"

    with open(eula_path, "w") as eula_file:
        eula_file.write(EULA)
    Logger.debug(f"EULA file created at {eula_path}.")


def set_server_properties(installation_dir : str, mc_version : Version) -> None:
    """
    Create a server.properties file with default settings.

    :param installation_dir: Directory where the server is installed.
    """

    properties_path = f"{installation_dir}/server.properties"

    properties = Properties()

    properties["rcon.password"].set(secrets.token_hex(16))
    properties["rcon.port"].set("25575")
    properties["enable-rcon"].set("true")

    properties.save(properties_path, mc_version)
    Logger.debug(f"Server properties file created at {properties_path}.")



def install(installer_url : str, installation_dir : str, version : Version) -> None:
    """
    Install a Minecraft server using the provided installer URL.

    :param installer_url: URL to the installer JAR file.
    :param installation_dir: Directory where the server should be installed.
    """


    Logger.info(f"Installing Minecraft server using {installer_url} to {installation_dir}.")
    os.makedirs(installation_dir, exist_ok=True)
    os.chdir(installation_dir)

    filename = f"server-{version}.jar"
    Logger.trace(f"Server filename: {filename}")

    # Download the installer JAR file
    installer_path = f"/{installation_dir}/{filename}"
    Logger.trace(f"Downloading installer {installer_url} to {installer_path}.")
    subprocess.run(["curl", "-L", "-o", installer_path, installer_url], check=True, capture_output=True)
    Logger.debug(f"Server downloaded to {installer_path}.")

    # Set EULA and server properties
    set_eula(installation_dir)
    set_server_properties(installation_dir, version)

    Logger.info("Minecraft server installation completed successfully.")


def main():
    # Example usage
    installer_url = "https://piston-data.mojang.com/v1/objects/79493072f65e17243fd36a699c9a96b4381feb91/server.jar"
    installation_dir = "/var/minecraft/servers/test_vanilla"

    install(installer_url, installation_dir, Version(1, 20, 5))

if __name__ == "__main__":
    from gamuLogger import Levels
    Logger.set_level("stdout", Levels.TRACE)

    main()
