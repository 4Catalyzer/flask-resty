import flask

# -----------------------------------------------------------------------------


def get_response_meta():
    return getattr(flask.g, 'resty_response_meta', None)


def set_response_meta(**kwargs):
    meta = getattr(flask.g, 'resty_response_meta', {})
    meta.update(kwargs)
    flask.g.resty_response_meta = meta
