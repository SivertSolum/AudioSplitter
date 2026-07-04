# Minimal torch hook for AudioSplitter — avoids collect_submodules("torch") from the
# default contrib hook, which pulls in testing, distributed, ONNX, and other unused code.

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    is_module_satisfies,
)

if is_module_satisfies("PyInstaller >= 6.0"):
    from PyInstaller import compat
    from PyInstaller.utils.hooks import PY_DYLIB_PATTERNS, logger

    module_collection_mode = "pyz+py"
    warn_on_missing_hiddenimports = False

    datas = collect_data_files(
        "torch",
        excludes=[
            "**/*.h",
            "**/*.hpp",
            "**/*.cuh",
            "**/*.lib",
            "**/*.cpp",
            "**/*.pyi",
            "**/*.cmake",
        ],
    )
    binaries = collect_dynamic_libs(
        "torch",
        search_patterns=PY_DYLIB_PATTERNS + ["*.so.*"],
    )

    hiddenimports = [
        "torch",
        "torch._C",
        "torch._VF",
        "torch.autograd",
        "torch.autograd.function",
        "torch.backends",
        "torch.backends.cuda",
        "torch.backends.cudnn",
        "torch.cuda",
        "torch.cuda.amp",
        "torch.fft",
        "torch.hub",
        "torch.nn",
        "torch.nn.functional",
        "torch.nn.modules",
        "torch.random",
        "torch.serialization",
        "torch.sparse",
        "torch.storage",
        "torch.utils",
        "torch.utils.data",
        "torch.utils.data.dataloader",
        "torch.distributed",
        "torch.distributed.distributed_c10d",
        "torch.distributed.rpc",
        "torch.package",
        "torch.package._mangling",
        "torch._jit_internal",
        "torch._awaits",
        "torch._sources",
        "torch.futures",
    ]

    if compat.is_win:
        def _collect_mkl_dlls():
            conda_torch_dist = None
            if compat.is_conda:
                from PyInstaller.utils.hooks import conda_support

                try:
                    conda_torch_dist = conda_support.package_distribution("torch")
                except ModuleNotFoundError:
                    conda_torch_dist = None

            if conda_torch_dist:
                if "mkl" not in conda_torch_dist.dependencies:
                    return []
                from PyInstaller.utils.hooks import conda_support

                return conda_support.collect_dynamic_libs("mkl", dependencies=True)

            import packaging.requirements
            from _pyinstaller_hooks_contrib.compat import importlib_metadata

            dist = importlib_metadata.distribution("torch")
            requirements = [
                packaging.requirements.Requirement(req) for req in dist.requires or []
            ]
            requirements = [
                req.name for req in requirements if req.marker is None or req.marker.evaluate()
            ]
            if "mkl" not in requirements:
                return []

            try:
                dist = importlib_metadata.distribution("mkl")
            except importlib_metadata.PackageNotFoundError:
                return []

            requirements = [
                packaging.requirements.Requirement(req) for req in dist.requires or []
            ]
            requirements = [
                req.name for req in requirements if req.marker is None or req.marker.evaluate()
            ]
            requirements = ["mkl"] + requirements

            mkl_binaries = []
            for requirement in requirements:
                try:
                    req_dist = importlib_metadata.distribution(requirement)
                except importlib_metadata.PackageNotFoundError:
                    continue
                for dist_file in req_dist.files or []:
                    dll_file = req_dist.locate_file(dist_file).resolve()
                    if not dll_file.match("**/Library/bin/*.dll"):
                        continue
                    mkl_binaries.append((str(dll_file), "."))
            return mkl_binaries

        try:
            binaries += _collect_mkl_dlls()
        except Exception:
            logger.warning("hook-torch: failed to collect MKL DLLs!", exc_info=True)
