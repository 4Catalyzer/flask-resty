import marshmallow.utils
from marshmallow import fields

# -----------------------------------------------------------------------------


class RelatedItem(fields.Nested):
    """A nested object field that only requires the ID on load.

    This class is a wrapper around :py:class:`marshmallow.fields.Nested` that
    provides simplified semantics in the context of a normalized REST API.

    When dumping, this field will dump the nested object as normal. When
    loading, this field will do a partial load to retrieve just the ID. This is
    because, when interacting with a resource that has a relationship to
    existing instances of another resource, the ID is sufficient to uniquely
    identify instances of the other resource.
    """

    def _deserialize(self, value, *args, **kwargs):
        if self.many and not marshmallow.utils.is_collection(value):
            self.fail("type", input=value, type=value.__class__.__name__)

        # Do partial load of related item, as we only need the id.
        return self.schema.load(value, partial=True)

    def _validate_missing(self, value):
        # Do not display detailed error data on required fields in nested
        # schema - in this context, they're actually not required.
        super(fields.Nested, self)._validate_missing(value)


class DelimitedList(fields.List):
    """List represented as a comma-delimited string, for use with args_schema.

    Same as `marshmallow.fields.List`, except can load from either a list or
    a delimited string (e.g. "foo,bar,baz"). Directly taken from webargs:
    https://github.com/marshmallow-code/webargs/blob/de061e037285fd08a42d73be95bc779f2a4e3c47/src/webargs/fields.py#L47

    :param Field cls_or_instance: A field class or instance.
    :param str delimiter: Delimiter between values.
    :param bool as_string: Dump values to string.
    """

    delimiter = ","

    def __init__(
        self, cls_or_instance, delimiter=None, as_string=False, **kwargs
    ):
        super().__init__(cls_or_instance, **kwargs)

        self.delimiter = delimiter or self.delimiter
        self.as_string = as_string

    def _serialize(self, value, attr, obj):
        ret = super()._serialize(value, attr, obj)
        if self.as_string:
            return self.delimiter.join(format(each) for each in ret)

        return ret

    def _deserialize(self, value, attr, data, **kwargs):
        try:
            ret = (
                value
                if marshmallow.utils.is_iterable_but_not_string(value)
                else value.split(self.delimiter)
            )
        except AttributeError:
            self.fail("invalid")

        return super()._deserialize(ret, attr, data, **kwargs)
