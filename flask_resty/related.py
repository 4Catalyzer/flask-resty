from .exceptions import ApiError

# -----------------------------------------------------------------------------


class Related(object):
    def __init__(self, item_class=None, **kwargs):
        self._item_class = item_class
        self._resolvers = kwargs

    def resolve_related(self, data):
        for field_name, resolver in self._resolvers.items():
            value = data.get(field_name, None)
            if value is None:
                # If this field were required or non-nullable, the deserializer
                # would already have raised an exception.
                continue

            try:
                resolved = self.resolve_field(value, resolver)
            except ApiError as e:
                pointer = '/data/{}'.format(field_name)
                raise e.update({'source': {'pointer': pointer}})

            data[field_name] = resolved

        if self._item_class:
            return self._item_class(**data)

        return data

    def resolve_field(self, value, resolver):
        # marshmallow always uses lists here.
        many = isinstance(value, list)
        if many and not value:
            # As a tiny optimization, there's no need to resolve an empty list.
            return value

        if isinstance(resolver, Related):
            resolve_item = resolver.resolve_related
        else:
            resolve_item = resolver().resolve_related_item

        if many:
            return [resolve_item(item) for item in value]

        return resolve_item(value)
