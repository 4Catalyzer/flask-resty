import functools

from .filtering import ModelFilterField

# -----------------------------------------------------------------------------


def get_item_or_404(method=None, **decorator_kwargs):
    # Allow using this as either a decorator or a decorator factory.
    if method is None:
        return functools.partial(get_item_or_404, **decorator_kwargs)

    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        id = self.get_data_id(kwargs)
        item = self.get_item_or_404(id, **decorator_kwargs)

        # No longer need these; just the item is enough.
        for id_field in self.id_fields:
            del kwargs[id_field]

        return method(self, item, *args, **kwargs)

    return wrapped


# -----------------------------------------------------------------------------


def filter_function(field, **kwargs):
    def wrapper(function):
        filter_field = ModelFilterField(field, function, **kwargs)
        functools.update_wrapper(filter_field, function)
        return filter_field

    return wrapper
