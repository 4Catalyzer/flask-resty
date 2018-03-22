import functools

from .exceptions import ApiError

# -----------------------------------------------------------------------------


class RelatedId(object):
    def __init__(self, view_class, field_name):
        self._view_class = view_class
        self.field_name = field_name

    def create_view(self):
        # Separating this out saves instantiating the view multiple times for
        # list fields.
        return self._view_class()

    def resolve_related_id(self, view, id):
        return view.resolve_related_id(id)


class Related(object):
    def __init__(self, item_class=None, **kwargs):
        self._item_class = item_class
        self._resolvers = kwargs

    def resolve_related(self, data):
        for field_name, resolver in self._resolvers.items():
            if isinstance(resolver, RelatedId):
                data_field_name = resolver.field_name
            else:
                data_field_name = field_name

            if data_field_name not in data:
                # If this field were required, the deserializer would already
                # have raised an exception.
                continue

            # Remove the data field (in case it's different) so we can keep
            # just the output field.
            value = data.pop(data_field_name)

            if value is None:
                # Explicitly clear the related item if the value was None.
                data[field_name] = None
                continue

            try:
                resolved = self.resolve_field(value, resolver)
            except ApiError as e:
                pointer = '/data/{}'.format(data_field_name)
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
        elif isinstance(resolver, RelatedId):
            view = resolver.create_view()
            resolve_item = functools.partial(resolver.resolve_related_id, view)
        else:
            resolve_item = resolver().resolve_related_item

        if many:
            return [resolve_item(item) for item in value]

        return resolve_item(value)
