import flask

__all__ = ('get_response_meta', 'set_response_meta')

# -----------------------------------------------------------------------------


def get_response_meta():
    return getattr(flask.g, '_json_api_response_meta', None)


def set_response_meta(new_meta, **kwargs):
    meta = getattr(flask.g, '_json_api_response_meta', {})
    meta.update(new_meta, **kwargs)
    flask.g._json_api_response_meta = meta
