import functools

# -----------------------------------------------------------------------------


def get_item_or_404(func=None, **decorator_kwargs):
    """
    Similar to Django's :py:func:`django.shortcuts.get_object_or_404` but
    as a decorator. Decorating :py:meth:`ApiView.retrieve`,
    :py:meth:`ApiView.update` or :py:meth:`ApiView.destroy` replaces the `id`
    parameter of the decorated method with the `item` corresponding to the
    provided `id`.

    Behaves like a decorator factory if `func` is omitted.

    :param func: The function to decorate
    :type func: function or None
    :return: The decorated function or a decorator factory
    :rtype: function
    """
    # Allow using this as either a decorator or a decorator factory.
    if func is None:
        return functools.partial(get_item_or_404, **decorator_kwargs)

    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):
        id = self.get_data_id(kwargs)
        item = self.get_item_or_404(id, **decorator_kwargs)

        # No longer need these; just the item is enough.
        for id_field in self.id_fields:
            del kwargs[id_field]

        return func(self, item, *args, **kwargs)

    return wrapped
