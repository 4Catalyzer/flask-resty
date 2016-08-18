from . import context

# -----------------------------------------------------------------------------

META_KEY = 'meta'

# -----------------------------------------------------------------------------


def get_response_meta():
    return context.get_context_value(META_KEY, None)


def set_response_meta(**kwargs):
    meta = context.get_context_value(META_KEY, {})
    meta.update(kwargs)
    context.set_context_value(META_KEY, meta)
