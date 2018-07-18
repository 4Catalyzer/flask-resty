# flake8: noqa

"""Flask-Resty plugin for apispec.

Allows passing a Flask-Resty `view` to
`APISpec.add_path <apispec.APISpec.add_path>`
"""

from .declaration import ApiViewDeclaration, ModelViewDeclaration

try:
    from .plugin import FlaskRestyPlugin
except ImportError:
    pass
