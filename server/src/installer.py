import subprocess
import os


EULA="""#By changing the setting below to TRUE you are indicating your agreement to our EULA (https://aka.ms/MinecraftEULA).
eula=true
"""

SERVER_PROPERTIES="""#Minecraft server properties
allow-flight=false
allow-nether=true
broadcast-console-to-ops=true
broadcast-rcon-to-ops=true
difficulty=easy
enable-command-block=false
enable-jmx-monitoring=false
enable-query=false
enable-rcon=false
enable-status=true
enforce-secure-profile=true
enforce-whitelist=false
entity-broadcast-range-percentage=100
force-gamemode=false
function-permission-level=2
gamemode=survival
generate-structures=true
generator-settings={}
hardcore=false
hide-online-players=false
initial-disabled-packs=
initial-enabled-packs=vanilla
level-name=world
level-seed=
level-type=minecraft\:normal
max-chained-neighbor-updates=1000000
max-players=20
max-tick-time=60000
max-world-size=29999984
motd=A Minecraft Server
network-compression-threshold=256
online-mode=true
op-permission-level=4
player-idle-timeout=0
prevent-proxy-connections=false
pvp=true
query.port=25565
rate-limit=0
rcon.password=
rcon.port=25575
require-resource-pack=false
resource-pack=
resource-pack-prompt=
resource-pack-sha1=
server-ip=
server-port=25565
simulation-distance=10
spawn-animals=true
spawn-monsters=true
spawn-npcs=true
spawn-protection=16
sync-chunk-writes=true
text-filtering-config=
use-native-transport=true
view-distance=10
white-list=false
"""

def set_eula(installation_dir : str) -> None:
    """
    Patch the EULA file to accept the Minecraft EULA.
    
    :param installation_dir: Directory where the server is installed.
    """
    
    eula_path = f"{installation_dir}/eula.txt"
    
    with open(eula_path, "w") as eula_file:
        eula_file.write(EULA)
        

def set_server_properties(installation_dir : str) -> None:
    """
    Create a server.properties file with default settings.
    
    :param installation_dir: Directory where the server is installed.
    """
    
    properties_path = f"{installation_dir}/server.properties"
    
    with open(properties_path, "w") as properties_file:
        properties_file.write(SERVER_PROPERTIES)


def install(installer_url : str, installation_dir : str) -> None:
    """
    Install a Minecraft server using the provided installer URL.
    
    :param installer_url: URL to the installer JAR file.
    :param installation_dir: Directory where the server should be installed.
    """
    
    os.makedirs(installation_dir, exist_ok=True)
    os.chdir(installation_dir)
    
    filename = installer_url.split("/")[-1]
    
    # Download the installer JAR file
    installer_path = f"/{installation_dir}/{filename}"
    subprocess.run(["curl", "-L", "-o", installer_path, installer_url], check=True)

    # Run the installer with Java
    subprocess.run(["java", "-jar", installer_path, "--installServer"], check=True)
    
    # Remove the installer JAR file
    os.remove(installer_path)
    
    # Set EULA and server properties
    set_eula(installation_dir)
    set_server_properties(installation_dir)
    
    
    
if __name__ == "__main__":
    # Example usage
    installer_url = "https://maven.minecraftforge.net/net/minecraftforge/forge/1.20.1-47.0.0/forge-1.20.1-47.0.0-installer.jar"
    installation_dir = "/home/antoine/test/srv"
    
    install(installer_url, installation_dir)