import functools

# -----------------------------------------------------------------------------


def get_item_or_404(method=None, **decorator_kwargs):
    # Allow using this as either a decorator or a decorator factory.
    if method is None:
        return functools.partial(get_item_or_404, **decorator_kwargs)

    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        item = self.get_item_or_404(
            kwargs.pop(self.url_id_key), **decorator_kwargs
        )
        return method(self, item, *args, **kwargs)

    return wrapped
