from flask import _request_ctx_stack as context_stack

from .utils import UNDEFINED

# -----------------------------------------------------------------------------


def _get_resty_context():
    context = context_stack.top
    if not context:
        raise RuntimeError("working outside of request context")

    if not hasattr(context, "resty"):
        context.resty = {}

    return context.resty


# -----------------------------------------------------------------------------


def get(key, default=None):
    return _get_resty_context().get(key, default)


def set(key, value):
    _get_resty_context()[key] = value


def get_for_view(view, key, default=None):
    values = get(key, UNDEFINED)
    if values is UNDEFINED:
        return default

    return values.get(view, default)


def set_for_view(view, key, value):
    values = get(key, UNDEFINED)
    if values is UNDEFINED:
        values = {}

    values[view] = value
    set(key, values)
