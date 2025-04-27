import requests
from bs4 import BeautifulSoup
import re
import json
from typing import Any
from datetime import datetime
from gamuLogger import Logger, Levels

from version import Version

Logger.set_module("forge_reader")

RE_MC_VERSION = re.compile(r"^([0-9]+)\.([0-9]+)\.([0-9]+)$")
RE_FORGE_VERSION = re.compile(r"([0-9]+)\.([0-9]+)\.([0-9]+)(?:\.([0-9]+))?")

class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Version):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class WebInterface:
    base_url = "https://files.minecraftforge.net/net/minecraftforge/forge/"
    
    @staticmethod
    def get_mc_versions():
        """
        Fetches the list of Minecraft versions from the Forge website.
        """
        Logger.set_module("forge_reader.mc_versions")
        
        Logger.debug(f"Fetching {WebInterface.base_url} for Minecraft versions.")
        response = requests.get(WebInterface.base_url)
        if not response.ok:
            raise ConnectionError(f"Failed to fetch data from {WebInterface.base_url}. Status code: {response.status_code}")
        Logger.trace(f"Response status code: {response.status_code}")
        
        html_content = response.text
        
        Logger.trace("Scraping HTML content for Minecraft versions.")
        
        # find the first element with the class "sidebar-nav"
        soup = BeautifulSoup(html_content, 'html.parser')
        sidebar_nav = soup.find(class_="sidebar-nav")
        if not sidebar_nav:
            raise ValueError("No sidebar-nav found in the HTML.")
        # find all the links within the sidebar-nav
        links = sidebar_nav.find_all('a')
        # keep only the links where the text matches the regex
        mc_versions : dict[Version, str] = {} # version : web page relative path
        for link in links:
            match = RE_MC_VERSION.match(link.text)
            if match:
                Logger.trace(f"Found Minecraft version: {link.text}")
                mc_versions[Version.from_string(link.text)] = link['href']

        Logger.debug(f"Found {len(mc_versions)} Minecraft versions.")
        return mc_versions
    
    @staticmethod
    def get_forge_versions(page_path : str):
        """
        Fetches the content of a specific Minecraft version page.
        :param page_path: Relative path to the version page
        :return: HTML content of the page
        """
        Logger.set_module("forge_reader.forge_versions")
        
        Logger.debug(f"Fetching {WebInterface.base_url + page_path} for Forge versions.")
        
        response = requests.get(WebInterface.base_url + page_path)
        if not response.ok:
            raise ConnectionError(f"Failed to fetch data from {WebInterface.base_url + page_path}. Status code: {response.status_code}")
        Logger.trace(f"Response status code: {response.status_code}")
        
        Logger.trace("Scraping HTML content for Forge versions.")
        html_content = response.text
        # find element with class "download"
        soup = BeautifulSoup(html_content, 'html.parser')
        download_list = soup.find(class_="download-list") #this is a table
        # get tbody
        tbody = download_list.find('tbody')
        # get all rows
        rows = tbody.find_all('tr')
        
        forge_versions : dict[Version, dict[str, Any]] = {}
        
        for row in rows:
            data : dict[str, Any] = {}
            download_version = row.find('td', class_='download-version')
            # <td class="download-version">
            #     47.4.0
            #         <i class="promo-recommended promo-latest  fa"></i>
            # </td>
            promo_recommended = download_version.find('i', class_='promo-recommended')
            data['recommended'] = promo_recommended is not None
            promo_latest = download_version.find('i', class_='promo-latest')
            data['latest'] = promo_latest is not None
            bugged = download_version.find('i', class_='fa-bug')
            data['bugged'] = bugged is not None
            
            version = download_version.text.strip()
            version_match = RE_FORGE_VERSION.match(version)
            if not version_match:
                raise ValueError(f"Invalid Forge version format: {version}")
            version = version_match.group(0)
            
            download_time = row.find('td', class_='download-time')
            data['time'] = datetime.strptime(download_time['title'], "%Y-%m-%d %H:%M:%S")
            
            download_links = row.find('ul', class_='download-links')
            for link in download_links.find_all('li'):
                # get the one who has "Installer" in the text of the first <a> tag
                if "Installer" in link.a.text:
                    # get the href of the <a> with class "info-link"
                    info_link = link.find('a', class_='info-link')
                    if info_link:
                        data['installer'] = info_link['href']
                        break
            else:
                Logger.warning(f"No installer link found for forge version: {version}")
                continue
            Logger.trace(f"Found Forge version: {version}. Recommended: {data['recommended']}, Latest: {data['latest']}, Time: {data['time']}, Installer: {data['installer']}")
            
            forge_versions[Version.from_string(version)] = data
            
        Logger.debug(f"Found {len(forge_versions)} Forge versions.")
        return forge_versions
        

if __name__ == "__main__":
    
    Logger.set_level("stdout", Levels.DEBUG)
    
    mc_versions = WebInterface.get_mc_versions()
    # print(json.dumps(versions, indent=4, cls=JsonEncoder))
    
    for k,v in mc_versions.items():
        WebInterface.get_forge_versions(v)
        # print(json.dumps(versions, indent=4, cls=JsonEncoder))