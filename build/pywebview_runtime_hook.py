"""PyInstaller runtime hook: prepare pywebview/pythonnet on frozen Windows builds."""

import os
import sys

if sys.platform == "win32" and getattr(sys, "frozen", False):
    # pywebview's WinForms/WebView2 backend requires .NET Framework (netfx), not coreclr.
    os.environ.setdefault("PYTHONNET_RUNTIME", "netfx")
