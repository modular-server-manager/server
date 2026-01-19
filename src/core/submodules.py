import sys
import os
import re
import json
import importlib
from version import Version

from gamuLogger import Logger

from ..user_interface import BaseInterface

Logger.set_module("Core.Submodules")

PYTHON_BASE_PATH  = sys.prefix
PYTHON_LIB_PATH   = f"{PYTHON_BASE_PATH}/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"


def __get_module_name(dirname: str, version : Version) -> str:
    abs_path = f"{PYTHON_LIB_PATH}/{dirname}-{str(version)}.dist-info"
    if not os.path.exists(abs_path):
        raise ValueError(f"Module path does not exist: {abs_path}")
    with open(f"{abs_path}/METADATA", "r") as f:
        for line in f:
            if line.startswith("Name: "):
                return line[len("Name: "):].strip()
    raise ValueError(f"Could not find module name in METADATA for {dirname}-{str(version)}")

def __get_msm_version() -> Version:
    candidates = [c for c in os.listdir(PYTHON_LIB_PATH) if c.startswith("modular_server_manager-") and c.endswith(".dist-info")]
    if not candidates:
        raise ValueError("Could not find modular_server_manager module in site-packages")
    if len(candidates) > 1:
        raise ValueError("Multiple modular_server_manager modules found in site-packages")
    match = re.match(r"modular_server_manager-([\d\.]+)\.dist-info", candidates[0])
    if not match:
        raise ValueError("Could not parse modular_server_manager version from directory name")
    return Version.from_string(match.groups()[0])

def __load_compatibility_map(module_dir : str) -> dict[Version, dict[str, Version]]:
    abs_path = f"{PYTHON_LIB_PATH}/{module_dir}"
    if not os.path.exists(abs_path):
        raise ValueError(f"Module path does not exist: {abs_path}")
    with open(f"{abs_path}/compatibility.json", "r") as f:
        data = json.load(f)
    if "compatibility" not in data:
        raise ValueError(f"compatibility.json does not contain 'compatibility' key in {module_dir}")
    compatibility_map : dict[Version, dict[str, Version]] = {}
    for msm_version_str, compat_info in data["compatibility"].items():
        msm_version = Version.from_string(msm_version_str)
        min_module_version = Version.from_string(compat_info["min_module_version"])
        max_module_version = Version.from_string(compat_info["max_module_version"])
        compatibility_map[msm_version] = {
            "min_module_version": min_module_version,
            "max_module_version": max_module_version
        }
    return compatibility_map

def __is_version_allowed(module_dir : str, module_version: Version) -> bool:
    msm_version = __get_msm_version()
    compatibility_map = __load_compatibility_map(module_dir)
    if msm_version not in compatibility_map:
        return False
    min_version = compatibility_map[msm_version]["min_module_version"]
    max_version = compatibility_map[msm_version]["max_module_version"]
    return min_version <= module_version <= max_version
    
def __list_mods()  -> list[tuple[str, Version]]:
    result : list[tuple[str, Version]] = []
    for path in os.listdir(PYTHON_LIB_PATH):
        if path.startswith("modular_server_manager_") and path.endswith(".dist-info"):
            print(f"Found module: {path}")
            match = re.match(r"(modular_server_manager_[\w\d_+-]+)-([\d\.]+)\.dist-info", path)
            if not match:
                continue
            mod_name, mod_version = match.groups()
            result.append((mod_name, Version.from_string(mod_version)))
    return result


def __import_interface_module(module_dir: str) -> type[BaseInterface]:
    Logger.debug(f"Importing interface module: {module_dir}")
    try:
        module = importlib.import_module(module_dir)
        Interface : type[BaseInterface] = getattr(module, "Interface")
    except ImportError as e:
        raise ImportError(f"Could not import module {module_dir}: {str(e)}")
    else:
        Logger.info(f"Imported module: {module_dir}")
        return Interface

def import_all_interfaces() -> dict[str, type[BaseInterface]]:
    interfaces : dict[str, type[BaseInterface]] = {}
    mods = __list_mods()
    Logger.debug(f"Found {len(mods)} sub-modules in site-packages:\n" + "\n".join([f"- {mod[0]} {str(mod[1])}" for mod in mods]))
    for mod_dir, mod_version in mods:
        if __is_version_allowed(mod_dir, mod_version):
            interface_class = __import_interface_module(mod_dir)
            name = __get_module_name(mod_dir, mod_version)
            interfaces[name] = interface_class
    Logger.info(f"Imported {len(interfaces)} interface modules")
    return interfaces
