"""
This script builds a Python package using the `build` module.
It allows for passing additional arguments to the build command and
supports specifying a version number via command line arguments.
It also sets the `PACKAGE_VERSION` environment variable if a version is provided.
"""

import os
import subprocess
import sys

if "--version" in sys.argv:
    idx = sys.argv.index("--version")
    version = sys.argv[idx + 1]
    os.environ["PACKAGE_VERSION"] = version
    sys.argv.pop(idx)  # remove --version
    sys.argv.pop(idx)  # remove version value

cmd = [sys.executable, "-m", "build"] + sys.argv[1:]
print(" ".join(cmd))  # Print the command for debugging
subprocess.run(cmd, check=True, stderr=sys.stderr, stdout=sys.stdout)
