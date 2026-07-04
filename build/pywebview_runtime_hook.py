"""PyInstaller runtime hook: configure pythonnet before pywebview imports clr."""

import os
import sys

if sys.platform == "win32" and getattr(sys, "frozen", False):
    os.environ.setdefault("PYTHONNET_RUNTIME", "coreclr")
