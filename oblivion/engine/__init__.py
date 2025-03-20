import importlib
import pathlib

"""
from oblivion.celery_app import app as celery

celery.autodiscover_tasks(["oblivion.engine"])
pkg_dir = pathlib.Path(__file__).parent

for py_file in pkg_dir.glob("**/*.py"):
    if py_file.name.startswith("_") or py_file.name == "__init__.py":
        continue
    rel_path = py_file.relative_to(pkg_dir).with_suffix("")
    module = ".".join(["oblivion.engine"] + list(rel_path.parts))
    importlib.import_module(module)
"""
