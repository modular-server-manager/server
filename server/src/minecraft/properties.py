import os
from json import dumps
from typing import Any
from xml.etree.ElementTree import Element, fromstring

from gamuLogger import Logger
from version import Version

CONFIG_DIR = os.path.dirname(__file__)

PROPERTIES_FILE = f"{CONFIG_DIR}/properties.xml"

Logger.set_module('Mc Server.Properties')

class PropertyOption:
    def __init__(self, name: str, value: str, until: Version = None, introduced: Version = None):
        """
        Initialize a property option with a name and value.

        :param name: Option name.
        :param value: Option value.
        """
        self.__name = name
        self.__value = value
        self.__until = until
        self.__introduced = introduced
        Logger.trace(f"PropertyOption created: {self.__name}={self.__value}, until={self.__until}, introduced={self.__introduced}")

    @property
    def name(self) -> str:
        """
        Get the name of the option.

        :return: Option name.
        """
        return self.__name

    @property
    def value(self) -> str:
        """
        Get the value of the option.

        :return: Option value.
        """
        return self.__value

    @property
    def until(self) -> Version:
        """
        Get the version until which the option is valid.

        :return: Version object.
        """
        return self.__until
    @property
    def introduced(self) -> Version:
        """
        Get the version in which the option was introduced.

        :return: Version object.
        """
        return self.__introduced

    def __repr__(self) -> str:
        """
        Get the string representation of the option.

        :return: String representation of the option.
        """
        return f"PropertyOption(name={self.__name}, value={self.__value}, until={self.__until}, introduced={self.__introduced})"

    @classmethod
    def from_xml(cls, element: Element) -> 'PropertyOption':
        """
        Create a PropertyOption object from an XML element.

        `<option label="enable" value="true"/>`

        :param element: XML element representing the option.
        :return: PropertyOption object.
        """
        name = element.get('label')
        value = element.get('value')
        until = Version.from_string(element.get('until')) if element.get('until') else None
        introduced = Version.from_string(element.get('introduced')) if element.get('introduced') else None
        return cls(name, value, until, introduced)

class Property:
    def __init__(self, name: str, default: str, doc : str, introduced : Version, **kwargs):
        """
        Initialize a property with a name and default value.

        :param name: Property name.
        :param default: Default value of the property.
        """
        self.__name = name
        self.__default = default
        self.__doc = doc
        self.__introduced = introduced
        self.__data : dict[str, Any] = kwargs
        self.__value = None
        Logger.debug(f"Property created: '{self.__name}', default={self.__default}, introduced={self.__introduced}")

    def set(self, value: str):
        """
        Set the value of the property.

        :param value: New value for the property.
        """

        if "options" in self.__data:
            options : list[PropertyOption] = self.__data["options"]
            if all(option.value != value for option in options):
                raise ValueError(f"Invalid value '{value}' for property '{self.__name}'. Valid options are: {', '.join(option.value for option in options)}")

        if "min" in self.__data and int(value) < self.__data["min"]:
            raise ValueError(f"Value '{value}' for property '{self.__name}' is less than minimum {self.__data['min']}")
        if "max" in self.__data and int(value) > self.__data["max"]:
            raise ValueError(f"Value '{value}' for property '{self.__name}' is greater than maximum {self.__data['max']}")

        self.__value = value

    def get(self, mc_version : Version) -> str:
        """
        Get the value of the property.

        :return: Current value of the property.
        """
        Logger.trace(f"Getting value for property '{self.__name}' ({self.__value})")
        if self.__value is not None:
            return self.__value
        if "options" in self.__data:
            for option in self.__data["options"]:
                option : PropertyOption
                Logger.trace(f"Checking option '{option.name}' with value '{option.value}' against default '{self.__default}'\n{option.introduced} <= {mc_version} <= {option.until}")
                if  (option.until is None or mc_version < option.until ) \
                and (option.introduced is None or option.introduced <= mc_version) \
                and option.name == self.__default:
                    return option.value
        elif self.__default is not None:
                return self.__default

        raise ValueError(f"Property '{self.__name}' has no value set and no default value available.")

    def __int__(self) -> int:
        """
        Convert the property value to an integer if possible.

        :return: Integer value of the property.
        """
        if self.__value.isdigit():
            return int(self.__value)
        raise ValueError(f"Property '{self.__name}' cannot be converted to an integer.")

    def __str__(self) -> str:
        """
        Get the string representation of the property.

        :return: String representation of the property.
        """
        return self.__value if self.__value is not None else self.__default

    @classmethod
    def from_xml(cls, element: Element) -> 'Property':
        """
        Create a Property object from an XML element.

        ```
        <integer name="view-distance" default="10" doc="Sets the amount of world data the server sends the client, measured in chunks in each direction of the player." introduced="1.3.1" min="3" max="32"/>
        ```
        ```
        <boolean name="white-list" default="false" doc="Enables a whitelist on the server. With a whitelist enabled, users not on the whitelist cannot connect." introduced="1.7.2">
            <option label="enable" value="true"/>
            <option label="disable" value="false"/>
        </boolean>
        ```

        :param element: XML element representing the property.
        :return: Property object.
        """
        name = element.get('name')
        default = element.get('default')
        doc = element.get('doc')
        introduced = Version.from_string(element.get('introduced'))

        data = {}

        if 'min' in element.attrib:
            data['min'] = int(element.get('min'))
        if 'max' in element.attrib:
            data['max'] = int(element.get('max'))

        if options := [
            PropertyOption.from_xml(option) for option in element.findall('option')
        ]:
            data['options'] = options

        return cls(name, default, doc, introduced, **data)

    def __repr__(self) -> str:
        """
        Get the string representation of the property.

        :return: String representation of the property.
        """
        return f"Property(name={self.__name}, default={self.__default}, doc={self.__doc}, introduced={self.__introduced}, value={self.__value})"

    def to_string(self, mc_version : Version) -> str:
        """
        Get the string representation of the property.

        :return: String representation of the property.
        """
        str_value = self.get(mc_version)
        return f"{self.__name}={str_value}"

    @property
    def name(self) -> str:
        """
        Get the name of the property.

        :return: Property name.
        """
        return self.__name

    @property
    def default(self) -> str:
        """
        Get the default value of the property.

        :return: Default value of the property.
        """
        return self.__default

    @property
    def doc(self) -> str:
        """
        Get the documentation string of the property.

        :return: Documentation string.
        """
        return self.__doc

    @property
    def introduced(self) -> Version:
        """
        Get the version in which the property was introduced.

        :return: Version object.
        """
        return self.__introduced

    def to_json(self) -> str:
        """
        Convert the property to a JSON string.

        :return: JSON string representation of the property.
        """
        return dumps({
            'name': self.__name,
            'default': self.__default,
            'doc': self.__doc,
            'introduced': str(self.__introduced),
            'value': self.__value,
            **self.__data
        }, indent=4)


class Properties:
    def __init__(self):
        """
        Initialize the Properties object with XML data.
        :param xml_data: XML data as a string.
        """

        self.__properties : dict[str, Property] = {}

        with open(PROPERTIES_FILE, 'r') as file:
            xml_data = file.read()

        root = fromstring(xml_data)
        for element in root:
            if element.tag not in ['boolean', 'integer', 'string']:
                raise ValueError(f"Unknown property type: {element.tag}")
            p = Property.from_xml(element)
            self.__properties[p.name] = p

    def load(self, properties_file: str):
        """
        Load properties from a file.

        :param properties_file: Path to the properties file.
        """
        with open(properties_file, 'r') as file:
            for line in file:
                if line.startswith('#') or not line.strip():
                    continue
                key, value = line.strip().split('=', 1)
                key = key.strip()
                value = value.strip()
                if key in self.__properties:
                    self.__properties[key].set(value)
                else:
                    raise ValueError(f"Unknown property: {key}")

    def save(self, properties_file: str, mc_version: Version = None):
        """
        Save properties to a file.

        :param properties_file: Path to the properties file.
        """
        normalized_path = os.path.normpath(properties_file)
        with open(normalized_path, 'w') as file:
            file.write("#Minecraft server properties\n")
            for prop in self.properties(mc_version).values():
                file.write(f"{prop.to_string(mc_version)}\n")

    def __getitem__(self, key: str) -> Property:
        """
        Get a property by its name.

        :param key: Property name.
        :return: Property object.
        """
        return self.__properties[key]

    def properties(self, mc_version : Version = None) -> dict[str, Property]:
        """
        Get all properties.

        :return: Dictionary of properties.
        """
        if mc_version is None:
            return self.__properties
        return {k: v for k, v in self.__properties.items() if v.introduced <= mc_version}
