# -*- coding: utf-8 -*-


from pallets_sphinx_themes import get_version


# -- Project information -----------------------------------------------------

project = 'Flask-RESTy'
copyright = '2018, Jimmy Jia'
author = 'Jimmy Jia'
release, version = get_version('Flask-RESTy')


# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
]
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
language = None
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
pygments_style = 'sphinx'


# -- Options for HTML output -------------------------------------------------

html_theme = 'alabaster'
html_static_path = ['_static']
html_favicon = 'favicon.ico'
