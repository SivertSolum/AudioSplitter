# lameenc is a single extension module (.pyd), not a package directory.

from PyInstaller.utils.hooks import get_module_file_attribute

binaries = [(get_module_file_attribute("lameenc"), ".")]
hiddenimports = ["lameenc"]
