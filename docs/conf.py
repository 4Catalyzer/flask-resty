import os
import sys
from pallets_sphinx_themes import get_version

# -- Project information -----------------------------------------------------

project = "Flask-RESTy"
copyright = "2015-present, 4Catalyzer"
author = "4Catalyzer"
release, version = get_version("Flask-RESTy")

# -- General configuration ---------------------------------------------------

extensions = [
    "alabaster",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
]
templates_path = ["_templates"]
source_suffix = ".rst"
master_doc = "index"
language = None
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
pygments_style = "sphinx"
primary_domain = "py"
default_role = "py:obj"
todo_include_todos = True

# -- Options for HTML output -------------------------------------------------

html_theme = "alabaster"
html_static_path = ["_static"]
html_favicon = "favicon.ico"
html_theme_options = {
    "description": "Building blocks for REST APIs for Flask",
    "description_font_style": "italic",
    "extra_nav_links": [
        ("Flask-RESTy @ PyPI", "https://pypi.python.org/pypi/flask-resty"),
        ("Flask-RESTy @ GitHub", "https://github.com/4Catalyzer/flask-resty"),
        ("Issue Tracker", "https://github.com/4Catalyzer/flask-resty/issues"),
    ],
}

html_sidebars = {
    "index": [
        "about.html",
        "useful-links.html",
        "localtoc.html",
        "searchbox.html",
    ],
    "**": ["about.html", "localtoc.html", "relations.html", "searchbox.html"],
}

# -- Intersphinx -------------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "flask": ("http://flask.pocoo.org/docs/1.0/", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/latest/", None),
    "marshmallow": ("http://marshmallow.readthedocs.io/en/latest/", None),
}

# -- Autodoc -----------------------------------------------------------------

autodoc_member_order = "bysource"
sys.path.insert(0, os.path.abspath(".."))
