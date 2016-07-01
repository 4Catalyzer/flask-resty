from .exceptions import ApiError

# -----------------------------------------------------------------------------


class Related(object):
    def __init__(self, item_class=None, **kwargs):
        self._item_class = item_class
        self._view_classes = kwargs

    def resolve_related(self, data):
        for field_name, view_class in self._view_classes.items():
            value = data.get(field_name, None)
            if value is None:
                # If this field were required or non-nullable, the deserializer
                # would already have raised an exception.
                continue

            try:
                resolved = self.resolve_field(value, view_class)
            except ApiError as e:
                pointer = '/data/{}'.format(field_name)
                raise e.update({'source': {'pointer': pointer}})

            data[field_name] = resolved

        if self._item_class:
            return self._item_class(**data)

        return data

    def resolve_field(self, value, view_class):
        # marshmallow always uses lists here.
        many = isinstance(value, list)
        if many and not value:
            # As a tiny optimization, there's no need to resolve an empty list.
            return value

        if isinstance(view_class, Related):
            # This is not actually a view class.
            resolver = view_class.resolve_related
        else:
            resolver = view_class().resolve_related_item

        if many:
            return [resolver(item) for item in value]

        return resolver(value)
