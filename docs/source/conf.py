"""Sphinx configuration for the LabArchives API documentation."""

import re
import sys
from datetime import datetime
from email.utils import getaddresses
from importlib.metadata import metadata as _metadata
from importlib.metadata import version as _version
from pathlib import Path

_VERSION_TAG = r"^v(\d+\.\d+\.\d+)$"

sys.path.insert(0, str((Path(__file__).resolve().parents[2] / "src").resolve()))


def _set_release(_app, config) -> None:
    match = re.fullmatch(_VERSION_TAG, getattr(config, "smv_current_version", ""))
    if match:
        release_name = match.group(1)
        config.release = release_name
        config.version = ".".join(release_name.split(".")[:2])


def setup(app) -> None:
    """Add small deployment helpers for versioned documentation builds."""
    app.connect("config-inited", _set_release)


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "labapi"
_dist_metadata = _metadata(project)
author = _dist_metadata["Author-email"]
author_names = [name for name, _ in getaddresses([author])]

copyright = f"{datetime.now().year}, {' and '.join(author_names)}"  # noqa: A001

release = _version(project)
version = ".".join(release.split(".")[:2])

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx_multiversion",
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosummary",
    "sphinx.ext.githubpages",
    "sphinx_copybutton",
    "sphinx_design",
]

autodoc_mock_imports = ["installed_browsers", "selenium"]

templates_path = ["_templates"]
exclude_patterns = []

language = "en"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "breeze"
html_baseurl = "https://nimh-dsst.github.io/labapi/"
html_static_path = ["_static"]

# Versioned docs deployment
smv_branch_whitelist = r"^$"
smv_tag_whitelist = _VERSION_TAG

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "requests": ("https://requests.readthedocs.io/en/latest/", None),
    "lxml": ("https://lxml.de/apidoc/", None),
    "cryptography": ("https://cryptography.io/en/latest/", None),
    "selenium": ("https://www.selenium.dev/selenium/docs/api/py/", None),
}

# Autodoc settings
autodoc_typehints = "signature"  # Show type hints in function signatures
autodoc_typehints_format = "short"  # Use short type names (List instead of typing.List)
autodoc_member_order = "bysource"

# Suppress cross-reference warnings for re-exported classes
suppress_warnings = ["ref.python"]
