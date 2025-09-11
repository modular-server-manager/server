import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup, Tag
from cache import Cache
from gamuLogger import Logger
from version import Version

Logger.set_module("Mc Server.Web Interface")

RE_MC_VERSION = re.compile(r"^([0-9]+)\.([0-9]+)\.([0-9]+)$")
RE_FORGE_VERSION = re.compile(r"([0-9]+)\.([0-9]+)\.([0-9]+)(?:\.([0-9]+))?")

class WebInterface:
    base_mc_url = "https://mcversions.net"
    base_forge_url = "https://files.minecraftforge.net/net/minecraftforge/forge/"

    @classmethod
    @Cache(expire_in=timedelta(days=1)) # type: ignore
    def get_mc_versions(cls) -> List[Version]:
        """
        Fetches the list of Minecraft versions from the Forge website.
        """
        Logger.debug(f"Fetching {cls.base_mc_url} for Minecraft versions.")
        response = requests.get(cls.base_mc_url)
        if not response.ok:
            raise ConnectionError(f"Failed to fetch data from {cls.base_mc_url}. Status code: {response.status_code}")
        Logger.trace(f"Response status code: {response.status_code}")

        html_content = response.text

        Logger.trace("Scraping HTML content for Minecraft versions.")

        # find the first element with the class "sidebar-nav"
        soup = BeautifulSoup(html_content, 'html.parser')
        # find the element with "Stable Releases" in the text
        stable_list_header = soup.find(string="Stable Releases") # type: ignore
        if not stable_list_header:
            raise ValueError("Could not find 'Stable Releases' section in the HTML content.")
        Logger.trace("Found 'Stable Releases' section in the HTML content.")
        # get the next element after stable_list_header, which should be a <div>"
        stable_list = stable_list_header.next # type: ignore
        if not stable_list:
            raise ValueError("Could not find the 'Stable Releases' list in the HTML content.")
        Logger.trace("Found 'Stable Releases' list in the HTML content.")

        mc_versions : List[Version] = []
        for element in stable_list.find_all("div", recursive=False):
            version_element : Tag = next(element.children).find('p')
            if not version_element:
                Logger.trace("Found an element without a version number, skipping.")
                continue
            #get the text without inner HTML tags. example :
            # <p class="text-xl leading-snug font-semibold"><span role="img" aria-label="sparkle">✨</span>1.21.5<br><span class="text-blue-300 text-xs"><time datetime="2025-03-25T12:14:58.000Z">2025-03-25</time></span></p>
            for child in version_element.children:
                if isinstance(child, str):
                    version_text = child
                    if version_text:
                        break
            if version_text == "No versions found":
                continue
            if version_text.count('.') == 1:
                version_text = f"{version_text.strip()}.0"
            if not (version_match := RE_MC_VERSION.match(version_text)):
                raise ValueError(f"Invalid Minecraft version format: {version_text}")

            version = Version.from_string(version_match.group(0))
            mc_versions.append(version)
            Logger.debug(f"Found Minecraft version: {version}")
        Logger.debug(f"Found {len(mc_versions)} Minecraft versions.")
        return mc_versions

    @classmethod
    @Cache(expire_in=timedelta(days=1)) # type: ignore
    def get_forge_versions(cls, mc_version : Version) -> Dict[Version, dict[str, bool|datetime|str]]:
        """
        Fetches the content of a specific Minecraft version page.
        :param page_path: Relative path to the version page
        :return: HTML content of the page
        """

        page_path = f"index_{mc_version}.html"

        Logger.debug(f"Fetching {cls.base_forge_url + page_path} for Forge versions.")

        response = requests.get(cls.base_forge_url + page_path)
        if not response.ok:
            raise ConnectionError(f"Failed to fetch data from {cls.base_forge_url + page_path}. Status code: {response.status_code}")
        Logger.trace(f"Response status code: {response.status_code}")

        Logger.trace("Scraping HTML content for Forge versions.")
        html_content = response.text
        # find element with class "download"
        soup = BeautifulSoup(html_content, 'html.parser')
        download_list = soup.find(class_="download-list") #this is a table
        # get tbody
        tbody = download_list.find('tbody') # type: ignore
        # get all rows
        rows = tbody.find_all('tr') # type: ignore

        forge_versions : dict[Version, dict[str, Any]] = {}

        for row in rows:
            data : dict[str, Any] = {}
            download_version = row.find('td', class_='download-version') # type: ignore
            promo_recommended = download_version.find('i', class_='promo-recommended') # type: ignore
            data['recommended'] = promo_recommended is not None
            promo_latest = download_version.find('i', class_='promo-latest') # type: ignore
            data['latest'] = promo_latest is not None
            bugged = download_version.find('i', class_='fa-bug') # type: ignore
            data['bugged'] = bugged is not None

            version = download_version.text.strip() # type: ignore
            version_match = RE_FORGE_VERSION.match(version)
            if not version_match:
                raise ValueError(f"Invalid Forge version format: {version}")
            version = version_match.group(0)
            version = Version.from_string(version)

            download_time = row.find('td', class_='download-time') # type: ignore
            data['time'] = datetime.strptime(download_time['title'], "%Y-%m-%d %H:%M:%S") # type: ignore

            download_links = row.find('ul', class_='download-links') # type: ignore
            for link in download_links.find_all('li'): # type: ignore
                # get the one who has "Installer" in the text of the first <a> tag
                if "Installer" in link.a.text: # type: ignore
                    if info_link := link.find('a', class_='info-link'): # type: ignore
                        data['installer'] = info_link['href'] # type: ignore
                        break
            else:
                Logger.warning(f"No installer link found for forge version: {version}")
                continue
            Logger.debug(f"Found Forge version: {version}.")
            Logger.trace(f"Recommended: {data['recommended']}, Latest: {data['latest']}, Bugged: {data['bugged']}, Time: {data['time']}, Installer: {data['installer']}")

            forge_versions[version] = data

        Logger.debug(f"Found {len(forge_versions)} Forge versions.")
        return forge_versions

    @classmethod
    @Cache(expire_in=timedelta(days=1)) # type: ignore
    def get_mc_installer_url(cls, mc_version: Version, _: Version = None) -> str:
        """
        Fetches the installer URL for a specific Minecraft and Forge version.
        :param mc_version: Minecraft version
        :param forge_version: Forge version
        :return: Installer URL
        """
        mc_versions = cls.get_mc_versions()
        if mc_version not in mc_versions:
            raise ValueError(f"Invalid Minecraft version: {mc_version}")

        url = f"{cls.base_mc_url}/download/{str(mc_version)}"

        Logger.debug(f"Fetching {url} to get the installer link for Minecraft {mc_version}.")

        response = requests.get(url)
        if not response.ok:
            raise ConnectionError(f"Failed to fetch data from {url}. Status code: {response.status_code}")
        Logger.trace(f"Response status code: {response.status_code}")
        html_content = response.text
        Logger.trace("Scraping HTML content for the installer link.")
        soup = BeautifulSoup(html_content, 'html.parser')
        if download_btn := soup.find("a", string="Download Server Jar"):
            return download_btn['href']
        else:
            raise ValueError("Could not find 'Download Server Jar' link in the HTML content.")

    @classmethod
    @Cache(expire_in=timedelta(days=1)) # type: ignore
    def get_forge_installer_url(cls, mc_version: Version, forge_version: Version) -> str:
        """
        Fetches the installer URL for a specific Minecraft and Forge version.  
        :param mc_version: The Minecraft version to get the Forge installer for  
        :param forge_version: The version of Forge to get the installer for  
        :return: The URL of the Forge installer for the specified Minecraft version
        """
        mc_versions : List[Version] = cls.get_mc_versions()
        if mc_version not in mc_versions:
            raise ValueError(f"Invalid Minecraft version: {mc_version}")

        forge_versions : Dict[Version, dict[str, bool|datetime|str]] = cls.get_forge_versions(mc_version)
        if forge_version not in forge_versions:
            raise ValueError(f"Invalid Forge version: {forge_version}")

        return forge_versions[forge_version]['installer']

    @classmethod
    @Cache(expire_in=timedelta(days=1)) # type: ignore
    def get_fabric_installer_url(cls, mc_version: Version, fabric_version: Version) -> str:
        """
        Fetches the Fabric installer URL for a specific Minecraft version.
        :param mc_version: Minecraft version
        :return: Fabric installer URL
        """
        raise NotImplementedError("Fabric installer URL fetching is not implemented yet.")