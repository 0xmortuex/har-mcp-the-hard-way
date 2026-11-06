"""Let a module's main.py import the code written in earlier modules.

Module directories have names like "02-streaming-json", which Python cannot import as
packages, so each main.py just puts the earlier directories on sys.path:

    import modpath; modpath.use("01-har-anatomy", "02-streaming-json")
"""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def use(*dirs: str) -> None:
    for d in (ROOT, *(os.path.join(ROOT, x) for x in dirs)):
        if d not in sys.path:
            sys.path.insert(0, d)
