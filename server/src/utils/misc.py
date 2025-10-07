import datetime as dt
import random

from gamuLogger import Logger, debug_func

Logger.set_module("Utils.Misc")

def str2bool(v : str) -> bool:
    """
    Convert a string to a boolean value.
    """
    if isinstance(v, bool):
        return v
    if v.lower() in {'yes', 'true', 't', '1'}:
        return True
    if v.lower() in {'no', 'false', 'f', '0'}:
        return False
    raise ValueError(f"Invalid boolean string: {v}")

def time_from_now(delta : dt.timedelta) -> dt.datetime:
    """
    return a datetime object from a string corresponding to a time from now
    """
    return dt.datetime.now() + delta

class NoLog:
    def write(self, *_): pass
    def flush(self): pass

def __get_class_name(full_path : str) -> str:
    return full_path.split(".")[-1] if "." in full_path else full_path

def _split_top_level_args(s: str) -> list[str]:
    """
    Splits a string like 'str, dict[str, int]' into ['str', 'dict[str, int]'],
    only splitting at the top-level comma.
    """
    args = []
    depth = 0
    last = 0
    for i, c in enumerate(s):
        if c in "[(":
            depth += 1
        elif c in "])":
            depth -= 1
        elif c == "," and depth == 0:
            args.append(s[last:i].strip())
            last = i + 1
    args.append(s[last:].strip())
    return args

def is_types_equals(a: str, b : str) -> bool:
    """
    Check if two types are equal
    list[Version] and list[version.version.Version] are considered equal,
    but list[Version] is different from list[str] or list[int].
    typing.Dict[version.version.Version, typing.Dict[str, typing.Any]] and Dict[Version, Dict[str, Any]] are considered equal.
    """
    a = a.replace("typing.", "").replace("typing_extensions.", "")
    b = b.replace("typing.", "").replace("typing_extensions.", "")


    if a == b:
        return True

    # Handle list and tuple types
    if (a.startswith("list[") or a.startswith("List[")) and (b.startswith("list[") or b.startswith("List[")):
        return is_types_equals(a[5:-1], b[5:-1])
    if (a.startswith("tuple[") or a.startswith("Tuple[")) and (b.startswith("tuple[") or b.startswith("Tuple[")):
        return is_types_equals(a[6:-1], b[6:-1])

    # Handle dict types
    if (a.startswith("dict[") or a.startswith("Dict[")) and (b.startswith("dict[") or b.startswith("Dict[")):
        args_a = _split_top_level_args(a[5:-1])
        args_b = _split_top_level_args(b[5:-1])
        if len(args_a) != 2 or len(args_b) != 2:
            return False
        return is_types_equals(args_a[0], args_b[0]) and is_types_equals(args_a[1], args_b[1])

    # Handle typing.Dict
    if a.startswith("Typing.") or a.startswith("typing."):
        a = a.replace("Typing.", "typing.")
    if b.startswith("Typing.") or b.startswith("typing."):
        b = b.replace("Typing.", "typing.")

    # Check for class names
    class_name_a = __get_class_name(a)
    class_name_b = __get_class_name(b)

    return class_name_a.lower() == class_name_b.lower()


def gen_id(length: int = 16) -> str:
    """
    Generate a random hexadecimal ID of the specified length.
    Default length is 16 characters.
    """
    if length <= 0:
        raise ValueError("Length must be a positive integer")
    return ''.join(random.choice('0123456789abcdef') for _ in range(length))



def split_with_nested(s: str, sep: str = ",") -> list[str]:
    """
    Split a string by a separator, ignoring separators inside nested structures like [], {}, ().
    Example: "a,[b,[c,d]],e" -> ["a", "[b,[c,d]]", "e"]
    """
    parts = []
    current = []
    depth = 0
    for char in s:
        if char in "[{(":
            depth += 1
        elif char in "]})":
            depth -= 1
        if char == sep and depth == 0:
            parts.append(''.join(current).strip())
            current = []
        else:
            current.append(char)
    if current:
        parts.append(''.join(current).strip())
    return parts


def guess_type(filename: str) -> str:
    """
    Guess the MIME type of a file based on its extension.
    """
    mimetypes = {
        'html': 'text/html',
        'css': 'text/css',
        'js': 'application/javascript',
        'json': 'application/json',
        'png': 'image/png',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'svg': 'image/svg+xml',
        'webp': 'image/webp',
        'woff': 'font/woff',
        'woff2': 'font/woff2',
        'ttf': 'font/ttf',
        'otf': 'font/otf'
    }
    ext = filename.split('.')[-1].lower()
    if ext not in mimetypes:
        Logger.warning(f"Unknown file extension: {ext}, defaulting to application/octet-stream")
        return 'application/octet-stream'
    return mimetypes[ext]




if __name__ == "__main__":
    # # test is_types_equals
    # assert is_types_equals("list[Version]", "list[version.version.Version]") is True
    # assert is_types_equals("list[Version]", "list[str]") is False
    # assert is_types_equals("list[Version]", "list[version.Version]") is True
    # assert is_types_equals("Version", "version.version.Version") is True
    # assert is_types_equals("Version", "str") is False
    # assert is_types_equals("int", "int") is True
    # assert is_types_equals("list[list[Version]]", "list[list[str]]") is False

    # assert is_types_equals("dict[str, Version]", "dict[str, version.version.Version]") is True
    # assert is_types_equals("dict[str, Version]", "dict[str, str]") is False

    # assert is_types_equals("tuple[Version, str]", "tuple[version.version.Version, str]") is True
    # assert is_types_equals("tuple[Version, str]", "tuple[str, str]") is False
    # assert is_types_equals("Typing.Dict[version.version.Version, str]", "Dict[Version, str]") is True
    
    # test split_with_nested
    assert split_with_nested("a,b,c") == ["a", "b", "c"]
    assert split_with_nested("a,[b,c],d") == ["a", "[b,c]", "d"]
    assert split_with_nested("a,{b,c},d") == ["a", "{b,c}", "d"]
    assert split_with_nested("a,(b,c),d") == ["a", "(b,c)", "d"]
    assert split_with_nested("a,[b,{c,d}],e") == ["a", "[b,{c,d}]", "e"]
    assert split_with_nested("a,[b,(c,d)],e") == ["a", "[b,(c,d)]", "e"]
    assert split_with_nested("a,[b,c],d,{e,f},g") == ["a", "[b,c]", "d", "{e,f}", "g"]
    assert split_with_nested("a,[b,c],d,(e,f),g") == ["a", "[b,c]", "d", "(e,f)", "g"]
    assert split_with_nested("a,[b,c],d,{e,(f,g)},h") == ["a", "[b,c]", "d", "{e,(f,g)}", "h"]
    print("All tests passed.")