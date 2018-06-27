from flask import _request_ctx_stack as context_stack

# -----------------------------------------------------------------------------


def _get_resty_context():
    context = context_stack.top

    if context:
        if not hasattr(context, 'resty'):
            context.resty = {}

        return context.resty


# -----------------------------------------------------------------------------


def get(key, default=None):
    return _get_resty_context().get(key, default)


def set(key, value):
    _get_resty_context()[key] = value
