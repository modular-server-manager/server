import re

RE_DICT_TYPE = re.compile(r"^[Dd]ict\[(.*)]$") # Matches dict types like Dict[str, int] or dict[int, str]
RE_LIST_TYPE = re.compile(r"^[Ll]ist\[(.*)]$") # Matches list types like List[str] or list[int]
RE_TUPLE_TYPE = re.compile(r"^[Tt]uple\[(.*)]$") # Matches tuple types like Tuple[str, int] or tuple[int, str]

RE_ENCODED_DICT = re.compile(r"^\{(.*)\}$") # Matches encoded dicts like {key1:value1,key2:value2}
RE_ENCODED_LIST = re.compile(r"^\[(.*)\]$") # Matches encoded lists like [item1,item2,item3]
RE_ENCODED_TUPLE = re.compile(r"^\((.*)\)$") # Matches encoded tuples like (item1,item2)

RE_NUMBER = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$") # Matches integers and floats, including negative numbers

RE_MC_SERVER_LOG_TEXT = re.compile(r"^.*\[[0-9]{2}:[0-9]{2}:[0-9]{2}\] \[.*/([A-Z]+)\] \[.*/(.*)\]: (.*)$") # first match is a color code, second match is the text
RE_JAVA_EXCEPTION = re.compile(r"^Exception in thread\s+\"(.*)\"\s+(.*):\s+(.*)$") # Matches Java exception lines like 'Exception in thread "main" java.lang.Exception: message'