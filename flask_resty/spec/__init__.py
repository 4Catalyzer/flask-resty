# flake8: noqa

"""Flask-Resty plugin for apispec.

Allows passing a Flask-Resty `view` to
`APISpec.add_path <apispec.APISpec.add_path>`
"""

from .plugin import FlaskRestyPlugin
from .declaration import ApiViewDeclaration, ModelViewDeclaration
