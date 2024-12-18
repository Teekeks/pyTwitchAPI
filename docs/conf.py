# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
import aiohttp
import datetime
sys.path.insert(0, os.path.abspath('..'))


# -- Project information -----------------------------------------------------

project = 'twitchAPI'
copyright = f'{datetime.date.today().year}, Lena "Teekeks" During'
author = 'Lena "Teekeks" During'

# The full version, including alpha/beta/rc tags
release = None
with open('../twitchAPI/__init__.py') as f:
    for line in f.readlines():
        if line.startswith('__version__'):
            release = 'v' + line.split('= \'')[-1][:-2].strip()
if release is None:
    release = 'dev'

language = 'en'

master_doc = 'index'

add_module_names = True

show_warning_types = True


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx_autodoc_typehints',
    'sphinx.ext.intersphinx',
    'sphinx.ext.autosummary',
    'enum_tools.autoenum',
    'recommonmark',
    'sphinx_paramlinks'
]

aiohttp.client.ClientTimeout.__module__ = 'aiohttp'
aiohttp.ClientTimeout.__module__ = 'aiohttp'

autodoc_member_order = 'bysource'
autodoc_class_signature = 'separated'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'aio': ('https://docs.aiohttp.org/en/stable/', None)
}

rst_epilog = """
.. |default| raw:: html 
    
    <div class="default-value-section"> <span class="default-value-label">Default:</span>

.. |br| raw:: html
    
    <br>
"""


def setup(app):
    app.add_css_file('css/custom.css')


html_theme = 'pydata_sphinx_theme'

# Define the json_url for our version switcher.
json_url = "/en/latest/_static/switcher.json"

# Define the version we use for matching in the version switcher.
version_match = os.environ.get("READTHEDOCS_VERSION")
# If READTHEDOCS_VERSION doesn't exist, we're not on RTD
# If it is an integer, we're in a PR build and the version isn't correct.
if not version_match or version_match.isdigit():
    # For local development, infer the version to match from the package.
    # release = release
    if "-a" in release or "-b" in release or "rc" in release:
        version_match = "develop"
        # We want to keep the relative reference if we are in dev mode
        # but we want the whole url if we are effectively in a released version
        json_url = "/en/latest/_static/switcher.json"
    else:
        version_match = release

html_theme_options = {
    "switcher": {
        "json_url": json_url,
        "version_match": version_match,
    },
    "header_links_before_dropdown": 4,
    "navbar_center": ["version-switcher", "navbar-nav"],
    "github_url": "https://github.com/Teekeks/pyTwitchAPI",
    "pygments_dark_style": "monokai",
    "navbar_align": "left",
    "logo": {
        "text": "twitchAPI",
        "image_light": "logo.png",
        "image_dark": "logo.png"
    }
}
# remove left sidebar
html_sidebars = {
    "**": []
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
