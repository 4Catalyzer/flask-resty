import flask
from werkzeug.local import LocalProxy

# -----------------------------------------------------------------------------

current_api = LocalProxy(lambda: flask.current_app.extensions['jsonapiview'])

# -----------------------------------------------------------------------------


def if_none(value, default):
    if value is None:
        return default

    return value
