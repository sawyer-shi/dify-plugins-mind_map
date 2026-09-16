import os
import subprocess


def _matplotlib_supports_ignore_system_fonts():
    try:
        from importlib import metadata

        parts = metadata.version("matplotlib").split(".")
        major, minor = int(parts[0]), int(parts[1])
        return major > 3 or (major == 3 and minor >= 11)
    except Exception:
        return False


def import_matplotlib_agg():
    try:
        from gevent import monkey
    except ImportError:
        monkey = None

    use_native_window = (
        monkey is not None and not _matplotlib_supports_ignore_system_fonts()
    )
    saved = monkey.saved.get("subprocess") if use_native_window and monkey else None
    if saved:
        for name, value in saved.items():
            setattr(subprocess, name, value)

    try:
        os.environ.setdefault("MPLBACKEND", "Agg")
        if _matplotlib_supports_ignore_system_fonts():
            os.environ.setdefault("MPL_IGNORE_SYSTEM_FONTS", "1")
        import matplotlib
        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot
        import numpy
    finally:
        if monkey and saved:
            monkey.patch_subprocess()
