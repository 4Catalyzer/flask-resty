import functools

# -----------------------------------------------------------------------------


def get_item_or_404(method):
    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        item = self.get_item_or_404(kwargs.pop(self.url_id_key))
        return method(self, item, *args, **kwargs)

    return wrapped
