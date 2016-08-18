from flask import _app_ctx_stack as context_stack

# -----------------------------------------------------------------------------


def _get_resty_context():
    context = context_stack.top

    if context:
        if not hasattr(context, 'resty'):
            context.resty = {}

        return context.resty


# -----------------------------------------------------------------------------


def get_context_value(key, default):
    return _get_resty_context().get(key, default)


def set_context_value(key, value):
    _get_resty_context()[key] = value
