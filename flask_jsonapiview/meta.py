import flask

from . import utils

# -----------------------------------------------------------------------------


def get_response_meta():
    return getattr(flask.g, 'jsonapiview_response_meta', None)


def set_response_meta(**kwargs):
    meta = getattr(flask.g, 'jsonapiview_response_meta', {})

    render_key = utils.current_api.render_key
    meta.update((render_key(key), value) for key, value in kwargs.items())

    flask.g.jsonapiview_response_meta = meta
