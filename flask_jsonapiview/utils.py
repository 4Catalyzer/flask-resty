import flask
from werkzeug.local import LocalProxy

__all__ = ('current_api', 'if_none')

# -----------------------------------------------------------------------------

current_api = LocalProxy(lambda: flask.current_app.extensions['jsonapiview'])

# -----------------------------------------------------------------------------


def if_none(value, default):
    if value is None:
        return default

    return value
