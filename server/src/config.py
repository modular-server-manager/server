from json import load, dump
from abc import ABC, abstractmethod
from datetime import datetime
import re
import os

from gamuLogger import Logger

Logger.set_module("config")

class BaseConfig(ABC):
    RE_REFERENCE = re.compile(r'^\$\{([a-zA-Z0-9_.]+)\}$')
    def __init__(self):
        self._config = {}
        self._load()
        
    @abstractmethod
    def _load(self):
        """
        Load configuration
        """
        pass
    
    @abstractmethod
    def _save(self):
        """
        Save configuration
        """
        pass
    
    @abstractmethod
    def _reload(self):
        """
        Reload configuration
        """
        pass
    
    def get(self, key: str, /, default=None, set : bool = False):
        """
        Get the value of a configuration key.
        
        :param key: Configuration key.
        :param default: Default value if the key does not exist.
        :return: Configuration value.
        """
        Logger.trace(f"Getting config value for key: {key}")
        self._reload()
        key_tokens = key.split('.')
        config = self._config
        for token in key_tokens:
            if token in config:
                config = config[token]
            else:
                if default is None:
                    raise KeyError(f"Key '{key}' not found in configuration.")
                if set:
                    self.set(key, default)
                return default
        if isinstance(config, str):
            # Check for reference
            for match in self.RE_REFERENCE.finditer(config):
                ref_key = match.group(1)
                ref_value = self.get(ref_key)
                config = config.replace(match.group(0), str(ref_value))
        Logger.trace(f"Config value for key '{key}': {config}")
        return config
    
    def set(self, key: str, value):
        """
        Set the value of a configuration key.
        
        :param key: Configuration key.
        :param value: Configuration value.
        """
        Logger.trace(f"Setting config value for key: {key} to {value}")
        self._reload()
        key_tokens = key.split('.')
        config = self._config
        for token in key_tokens[:-1]:
            if token not in config:
                config[token] = {}
            config = config[token]
        config[key_tokens[-1]] = value
        self._save()
        return self
    
    def remove(self, key: str):
        """
        Remove a configuration key.
        
        :param key: Configuration key.
        """
        Logger.trace(f"Removing config key: {key}")
        self._reload()
        key_tokens = key.split('.')
        config = self._config
        for token in key_tokens[:-1]:
            if token in config:
                config = config[token]
            else:
                raise KeyError(f"Key '{key}' not found in configuration.")
        if key_tokens[-1] in config:
            del config[key_tokens[-1]]
        else:
            raise KeyError(f"Key '{key}' not found in configuration.")
        return self

class JSONConfig(BaseConfig):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._last_modified = None
        super().__init__()
    
    def _load(self):
        """
        Load configuration from a JSON file.
        """
        Logger.trace(f"Loading configuration from {self.file_path}")
        if not os.path.exists(self.file_path):
            self._config = {}
            self._save()
            return self
        with open(self.file_path, 'r') as file:
            self._config = load(file)
        return self
    
    def _reload(self):
        """
        Reload configuration from a JSON file if the modification time has changed.
        """
        if not os.path.exists(self.file_path):
            self._config = {}
            self._save()
            return self
        modified_time = os.path.getmtime(self.file_path)
        if self._last_modified is None or modified_time > self._last_modified.timestamp():
            Logger.trace(f"Reloading configuration from {self.file_path} due to modification time change")
            self._load()
            self._last_modified = datetime.fromtimestamp(modified_time)
        else:
            Logger.trace(f"Configuration file {self.file_path} has not changed since last load")
        return self
    
    def _save(self):
        """
        Save configuration to a JSON file.
        """
        Logger.trace(f"Saving configuration to {self.file_path}")
        with open(self.file_path, 'w') as file:
            dump(self._config, file, indent=4)
        self._last_modified = datetime.now()
        return self
