import re

RE_MC_SERVER_NAME = re.compile(r"^[a-zA-Z0-9_]{1,16}$") # Matches Minecraft server names (1-16 characters, letters, numbers, underscores)
