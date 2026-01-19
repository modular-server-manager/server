import subprocess

from ..vanilla.server import MinecraftServer


class ForgeServer(MinecraftServer):
    """
    Class to manage a Minecraft Forge server.
    """

    def _spawn_server_process(self):
        return subprocess.Popen(
            ["./run.sh", "--nogui"],
            cwd=self.path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
