from .exceptions import ApiError

# -----------------------------------------------------------------------------


class Related(object):
    def __init__(self, item_class=None, **kwargs):
        self._item_class = item_class
        self._resolvers = kwargs

    def resolve_related(self, data):
        related_data = dict(data)

        for field_name, resolver in self._resolvers.items():
            value = data.get(field_name, None)
            if value is None:
                # If this field were required or non-nullable, the deserializer
                # would already have raised an exception.
                continue

            try:
                resolved_field_name, resolved_value = self.resolve_field(
                    field_name, value, resolver,
                )
            except ApiError as e:
                pointer = '/data/{}'.format(field_name)
                raise e.update({'source': {'pointer': pointer}})

            if resolved_field_name != field_name:
                del related_data[field_name]
            related_data[resolved_field_name] = resolved_value

        if self._item_class:
            return self._item_class(**related_data)

        return related_data

    def resolve_field(self, field_name, value, resolver):
        # marshmallow always uses lists here.
        many = isinstance(value, list)

        # This isn't factored out to avoid repeatedly instantiating the view
        # class.
        if isinstance(resolver, Related):
            # Nested related field.
            resolve_item = resolver.resolve_related
        elif callable(resolver):
            # Assume this is a view class.
            resolve_item = resolver().resolve_related_item
        else:
            # Handle related IDs with renamed fields.
            view_class, field_name = resolver
            view = view_class()
            resolve_item = view.resolve_related_item
            if many:
                value = (view.get_id_dict(item) for item in value)
            else:
                value = view.get_id_dict(value)

        if many:
            resolved_value = [resolve_item(item) for item in value]
        else:
            resolved_value = resolve_item(value)
        return field_name, resolved_value
