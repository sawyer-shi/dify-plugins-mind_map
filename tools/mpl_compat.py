import os
import subprocess


def import_matplotlib_agg():
    try:
        from gevent import monkey
    except ImportError:
        monkey = None

    saved = monkey.saved.get("subprocess") if monkey else None
    if saved:
        for name, value in saved.items():
            setattr(subprocess, name, value)

    try:
        os.environ.setdefault("MPLBACKEND", "Agg")
        import matplotlib
        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot
        import numpy
    finally:
        if monkey and saved:
            monkey.patch_subprocess()
