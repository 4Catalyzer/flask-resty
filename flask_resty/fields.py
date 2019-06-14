import marshmallow.utils
from marshmallow import fields

from .compat import schema_load

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
        return schema_load(self.schema, value, partial=True)

    def _validate_missing(self, value):
        # Do not display detailed error data on required fields in nested
        # schema - in this context, they're actually not required.
        super(fields.Nested, self)._validate_missing(value)
