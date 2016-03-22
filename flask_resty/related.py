from .exceptions import ApiError

# -----------------------------------------------------------------------------


class Related(object):
    def __init__(self, **kwargs):
        self._view_classes = kwargs

    def __call__(self, data, view):
        for field_name, view_class in self._view_classes.items():
            many = view.deserializer.fields[field_name].many
            self.resolve_nested(data, field_name, view_class, many=many)

        return data

    def resolve_nested(self, data, field_name, view_class, many=False):
        try:
            nested_data = data[field_name]
        except KeyError:
            # If this field were required, the deserializer already would have
            # raised an exception.
            return

        if nested_data is None:
            # If this field were non-nullable, the deserializer already would
            # have raised an exception.
            data[field_name] = None
            return

        try:
            if many:
                if not nested_data:
                    resolved = []
                else:
                    view = view_class()
                    resolved = [
                        view.resolve_related_item(nested_datum)
                        for nested_datum in nested_data
                    ]
            else:
                resolved = view_class().resolve_related_item(nested_data)
        except ApiError as e:
            pointer = '/data/{}'.format(field_name)
            raise e.update({'source': {'pointer': pointer}})

        data[field_name] = resolved
