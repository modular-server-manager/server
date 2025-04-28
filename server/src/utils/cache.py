from datetime import datetime, timedelta

from gamuLogger import Logger

Logger.set_module("cache")

class Cache:
    """
    A simple decorator to cache the result of a function for a specified amount of time.
    """
    def __init__(self, expire_in: timedelta):
        self.expire_in = expire_in
        self.cache = {}
        
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            key = (args, frozenset(kwargs.items()))
            if key in self.cache:
                result, timestamp = self.cache[key]
                if datetime.now() - timestamp < self.expire_in:
                    Logger.trace(f"Using cached result for {func.__name__} with args {args} and kwargs {kwargs}")
                    return result
            Logger.trace(f"Cache miss for {func.__name__} with args {args} and kwargs {kwargs}")
            result = func(*args, **kwargs)
            self.cache[key] = (result, datetime.now())
            return result
        return wrapper
