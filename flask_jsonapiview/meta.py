import flask

from . import utils

__all__ = ('get_response_meta', 'set_response_meta')

# -----------------------------------------------------------------------------


def get_response_meta():
    return getattr(flask.g, 'jsonapiview_response_meta', None)


def set_response_meta(**kwargs):
    meta = getattr(flask.g, 'jsonapiview_response_meta', {})

    api = utils.current_api
    meta.update((api.render_key(key), value) for key, value in kwargs.items())

    flask.g.jsonapiview_response_meta = meta
