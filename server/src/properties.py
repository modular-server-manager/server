from typing import Any

class Properties:
    def __init__(self):
        self._properties : dict[str, Any] = {}

    @classmethod
    def from_file(cls, file_path: str):
        """
        Load properties from a file.
        
        :param file_path: Path to the properties file.
        :return: Properties object.
        """
        instance = cls()
        with open(file_path, 'r') as file:
            for line in file:
                if line.strip() and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    instance._properties[key.strip()] = value.strip()
        return instance
    
    def to_file(self, file_path: str):
        """
        Save properties to a file.
        
        :param file_path: Path to the properties file.
        """
        with open(file_path, 'w') as file:
            for key, value in self._properties.items():
                file.write(f"{key}={value}\n")
                
    def get(self, key: str, default=None):
        """
        Get the value of a property.
        
        :param key: Property key.
        :param default: Default value if the key does not exist.
        :return: Property value.
        """
        return self._properties.get(key, default)
    
    def set(self, key: str, value):
        """
        Set the value of a property.
        
        :param key: Property key.
        :param value: Property value.
        """
        self._properties[key] = value
        
    def remove(self, key: str):
        """
        Remove a property.
        
        :param key: Property key.
        """
        if key in self._properties:
            del self._properties[key]
        else:
            raise KeyError(f"Key '{key}' not found in properties.")
