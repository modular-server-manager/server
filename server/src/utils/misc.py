import datetime as dt

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