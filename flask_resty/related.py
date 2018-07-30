import functools

from .exceptions import ApiError

# -----------------------------------------------------------------------------


class RelatedId(object):
    """A facility for resolving model fields by id.

    :param view_class: The :py:class:`ModelView` corresponding to the related model.
    :param str field_name: The name of the field on the related model.
    """

    def __init__(self, view_class, field_name):
        self._view_class = view_class
        self.field_name = field_name

    def create_view(self):
        """Create an instance of the stored view. Separating this out saves
        instantiating the view multiple times for list fields.

        :return: The :py:class:`ModelView` instance.
        :rtype: object
        """
        return self._view_class()

    def resolve_related_id(self, view, id):
        """Resolves `id` by calling :py:meth:`ModelView.resolve_related_id`
        on the given `view`.

        :return: The resolved item.
        :rtype: object
        """
        return view.resolve_related_id(id)


class Related(object):
    """A facility for recursively resolving model fields.

    :param item_class: The SQLAlchemy mapper corresponding to the related item.
    :param kwargs: A mapping from related fields to a callable resolver. 
    :type kwargs: dict 
    """

    def __init__(self, item_class=None, **kwargs):
        self._item_class = item_class
        self._resolvers = kwargs

    def resolve_related(self, data):
        """Substitutes any related fields present in `data` with the result of
        calling :py:meth:`resolve_field` on the field's value.

        :param data object: The deserialized request data.
        :return: The deserialized data with related fields resolved.
        :rtype: object
        """
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
        """Applies `resolver` to the given value to resolve the related field.
        If `value` is a list, each item in the list will be resolved.

        :param value: The value corresponding to the field we are resolving.
        :param resolver: A callable capable of resolving the given `value`.
        :type resolver: :py:class:`Related` | :py:class:`RelatedId` | func
        """
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
