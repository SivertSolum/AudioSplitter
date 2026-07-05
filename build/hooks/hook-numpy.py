# NumPy hook for AudioSplitter frozen builds.
# Based on PyInstaller's upstream hook-numpy.py — collects binaries without
# pulling in the full numpy test suite (collect_all would bloat the bundle).

from PyInstaller import compat
from PyInstaller.utils.hooks import collect_dynamic_libs, get_installer
from packaging.version import Version

numpy_version = Version(compat.importlib_metadata.version("numpy")).release
numpy_installer = get_installer("numpy")

hiddenimports = [
    "numpy.core.multiarray",
    "numpy._core._multiarray_umath",
]
datas = []
binaries = collect_dynamic_libs("numpy")

if numpy_installer == "conda":
    from PyInstaller.utils.hooks import conda_support

    datas += conda_support.collect_dynamic_libs("numpy", dependencies=True)

if compat.is_win and numpy_version >= (1, 26) and numpy_installer != "conda":
    from PyInstaller.utils.hooks import collect_delvewheel_libs_directory

    datas, binaries = collect_delvewheel_libs_directory("numpy", datas=datas, binaries=binaries)

if numpy_version >= (2, 0):
    hiddenimports += ["numpy._core._dtype_ctypes", "numpy._core._multiarray_tests"]
else:
    hiddenimports += ["numpy.core._dtype_ctypes"]
    if numpy_version >= (1, 25):
        hiddenimports += ["numpy.core._multiarray_tests"]

if numpy_version >= (2, 3, 0):
    hiddenimports += ["numpy._core._exceptions"]

excludedimports = [
    "scipy",
    "pytest",
    "nose",
    "f2py",
    "setuptools",
]

if numpy_version < (1, 22, 0) or numpy_version > (1, 22, 1):
    excludedimports += [
        "distutils",
        "numpy.distutils",
    ]

if numpy_version < (2, 0):
    excludedimports += [
        "numpy.f2py",
    ]
