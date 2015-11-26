from sqlalchemy.orm.exc import NoResultFound

from .exceptions import ApiError

# -----------------------------------------------------------------------------


class RelatedBase(object):
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

        try:
            if many:
                if not nested_data:
                    resolved = []
                else:
                    view = view_class()
                    resolved = [
                        self.get_related_item(nested_datum, view)
                        for nested_datum in nested_data
                    ]
            else:
                resolved = self.get_related_item(nested_data, view_class())
        except ApiError as e:
            pointer = '/data/{}'.format(field_name)
            raise e.update({'source': {'pointer': pointer}})

        data[field_name] = resolved

    def get_related_item(self, related_data, related_view):
        related_id = self.get_related_id(related_data, related_view)

        try:
            related_item = related_view.get_item(related_id)
        except NoResultFound:
            raise ApiError(422, {'code': 'invalid_related.not_found'})

        return related_item

    def get_related_id(self, related_data, related_view):
        raise NotImplementedError()


class NestedRelated(RelatedBase):
    def get_related_id(self, related_data, related_view):
        try:
            related_id = related_data['id']
        except KeyError:
            raise ApiError(422, {'code': 'invalid_related.missing_id'})

        return related_id
