# flake8: noqa

"""Flask-Resty plugin for apispec. Allows passing a Flask-Resty
`view` to `APISpec.add_path <apispec.APISpec.add_path>`
"""

from .plugin import setup, schema_path_helper
from .declaration import *
from .utils import ref, flask_path_to_swagger, get_marshmallow_schema_name
