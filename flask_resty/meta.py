from . import context

# -----------------------------------------------------------------------------


def get_response_meta():
    return context.get("response_meta")


def update_response_meta(next_meta):
    if next_meta is None:
        return

    meta = get_response_meta()
    if meta is None:
        meta = {}

    meta.update(next_meta)
    context.set("response_meta", meta)
