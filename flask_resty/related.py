import functools

from .exceptions import ApiError

# -----------------------------------------------------------------------------


class RelatedId:
    """Resolve a related item by a scalar ID.

    :param view_class: The :py:class:`ModelView` corresponding to the related
        model.
    :param str field_name: The field name on request data.
    """

    def __init__(self, view_class, field_name):
        self._view_class = view_class
        self.field_name = field_name

    def create_view(self):
        # Separating this out saves instantiating the view multiple times for
        # list fields.
        return self._view_class()

    def resolve_related_id(self, view, id):
        return view.resolve_related_id(id)


class Related:
    """A component for resolving deserialized data fields to model instances.

    The `Related` component is responsible for resolving related model
    instances by ID and for constructing nested model instances. It supports
    multiple related types of functionality. For a view with::

        related = Related(
            foo=RelatedId(FooView, "foo_id"),
            bar=BarView,
            baz=Related(models.Baz, qux=RelatedId(QuxView, "qux_id"),
        )

    Given deserialized input data like::

        {
            "foo_id": "3",
            "bar": {"id": "4"},
            "baz": {name: "Bob", "qux_id": "5"},
            "other_field": "value",
        }

    This component will resolve these data into something like::

        {
            "foo": <Foo(id=3)>,
            "bar": <Bar(id=4)>,
            "baz": <Baz(name="Bob", qux=<Qux(id=5)>>,
            "other_field": "value",
        }

    In this case, the Foo, Bar, and Qux instances are fetched from the
    database, while the Baz instance is freshly constructed. If any of the Foo,
    Bar, or Qux instances do not exist, then the component will fail the
    request with a 422.

    Formally, in this specification:

    - A `RelatedId` item will retrieve the existing object in the database
      with the ID from the specified scalar ID field using the specified view.
    - A view class will retrieve the existing object in the database using the
      object stub containing the ID fields from the data field of the same
      name, using the specified view. This is generally used with the
      `RelatedItem` field class, and unlike `RelatedId`, supports composite
      IDs.
    - Another `Related` item will apply the same resolution to a nested
      dictionary. Additionally, if the `Related` item is given a callable as
      its positional argument, it will construct a new instance given that
      callable, which can often be a model class.

    `Related` depends on the deserializer schema to function accordingly, and
    delegates validation beyond the database fetch to the schema. `Related`
    also automatically supports cases where the fields are list fields or are
    configured with ``many=True``. In those cases, `Related` will iterate
    through the sequence and resolve each item in turn, using the rules as
    above.

    :param item_class: The SQLAlchemy mapper corresponding to the related item.
    :param dict kwargs: A mapping from related fields to a callable resolver.
    """

    def __init__(self, item_class=None, **kwargs):
        self._item_class = item_class
        self._resolvers = kwargs

    def resolve_related(self, data):
        """Resolve the related values in the request data.

        This method will replace values in `data` with resolved model
        instances as described above. This operates in place and will mutate
        `data`.

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
                pointer = f"/data/{data_field_name}"
                raise e.update({"source": {"pointer": pointer}})

            data[field_name] = resolved

        if self._item_class:
            return self._item_class(**data)

        return data

    def resolve_field(self, value, resolver):
        """Resolve a single field value.

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

    def __or__(self, other):
        """Combine two `Related` instances.

        `Related` supports view inheritance by implementing the `|` operator.
        For example, `Related(foo=..., bar=...) | Related(baz=...)` will create
        a new `Related` instance with resolvers for each `foo`, `bar` and
        `baz`. Resolvers on the right-hand side take precedence where each
        `Related` instance has the same key.
        """
        if not isinstance(other, Related):
            return NotImplemented

        return self.__class__(
            other._item_class or self._item_class,
            **{**self._resolvers, **other._resolvers},
        )
