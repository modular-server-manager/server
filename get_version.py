
def install_if_not_installed(package_name, url):
    try:
        __import__(package_name)
    except ImportError:
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", url])



install_if_not_installed("version", "https://github.com/T0ine34/python-sample/releases/download/1.0.2/version-1.0.2-py3-none-any.whl")


import os

from version import Version

branch = os.popen("git rev-parse --abbrev-ref HEAD").read().strip()

def get_tag():
    tags_list = os.popen("git tag").read().strip().split("\n")
    tags = [Version.from_string(t) for t in tags_list if t]
    tags.sort(reverse=True)
    return tags[0] if tags else Version(0, 0, 0)

try:
    version = Version.from_string(branch)
except ValueError:
    version = get_tag()
    version.prerelease = "alpha"

    if version.minor >= 1:
        version.patch_increment()
    else:
        version.minor_increment()

last_commit = os.popen("git rev-parse HEAD").read().strip()

version.metadata = last_commit
print(version)
