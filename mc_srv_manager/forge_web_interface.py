import requests
from bs4 import BeautifulSoup
import re
from version import Version
import json
from typing import Any
from datetime import datetime

RE_VERSION = re.compile(r"^([0-9]+)\.([0-9]+)\.([0-9]+)$")

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
        response = requests.get(WebInterface.base_url)
        response.raise_for_status()
        html_content = response.text
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
            match = RE_VERSION.match(link.text)
            if match:
                mc_versions[Version.from_string(link.text)] = link['href']
        # sort the versions

        return mc_versions
    
    @staticmethod
    def get_forge_versions(page_path : str):
        """
        Fetches the content of a specific Minecraft version page.
        :param page_path: Relative path to the version page
        :return: HTML content of the page
        """
        response = requests.get(WebInterface.base_url + page_path)
        response.raise_for_status()
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
            
            version = download_version.text.strip()
            
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
            
            forge_versions[Version.from_string(version)] = data
            
        return forge_versions
        

if __name__ == "__main__":
    # versions = {str(k) : v for k,v in WebInterface.get_mc_versions().items()}
    # print(json.dumps(versions, indent=4, cls=JsonEncoder))
    
    versions = {str(k) : v for k,v in WebInterface.get_forge_versions("index_1.20.1.html").items()}
    print(json.dumps(versions, indent=4, cls=JsonEncoder))