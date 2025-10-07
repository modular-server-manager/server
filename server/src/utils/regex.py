import re

RE_MC_SERVER_NAME = re.compile(r"^[a-zA-Z0-9_]{1,16}$") # Matches Minecraft server names (1-16 characters, letters, numbers, underscores)

RE_DICT_TYPE = re.compile(r"^[Dd]ict\[(.*)]$") # Matches dict types like Dict[str, int] or dict[int, str]
RE_LIST_TYPE = re.compile(r"^[Ll]ist\[(.*)]$") # Matches list types like List[str] or list[int]
RE_TUPLE_TYPE = re.compile(r"^[Tt]uple\[(.*)]$") # Matches tuple types like Tuple[str, int] or tuple[int, str]

RE_ENCODED_DICT = re.compile(r"^\{(.*)\}$") # Matches encoded dicts like {key1:value1,key2:value2}
RE_ENCODED_LIST = re.compile(r"^\[(.*)\]$") # Matches encoded lists like [item1,item2,item3]
RE_ENCODED_TUPLE = re.compile(r"^\((.*)\)$") # Matches encoded tuples like (item1,item2)