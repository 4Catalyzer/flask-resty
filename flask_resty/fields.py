from marshmallow import fields, ValidationError
import marshmallow.utils

# -----------------------------------------------------------------------------


class RelatedItem(fields.Nested):
    """Wrapper around :py:class:`marshmallow.fields.Nested` that provides
    simplified semantics in the context of a normalized REST API.

    When interacting with a resource that has a relationship to another
    resource we should only have to use the primary key of the related
    resource.

    A :py:class:`RelatedItem` will perform a partial load when it is
    deserialized so that we can omit most of the data on the related resoure
    in our API interactions.
    """
    def _deserialize(self, value, attr, data):
        if self.many and not marshmallow.utils.is_collection(value):
            self.fail('type', input=value, type=value.__class__.__name__)

        # Do partial load of related item, as we only need the id.
        data, errors = self.schema.load(value, partial=True)
        if errors:
            raise ValidationError(errors, data=data)
        return data

    def _validate_missing(self, value):
        # Do not display detailed error data on required fields in nested
        # schema - in this context, they're actually not required.
        super(fields.Nested, self)._validate_missing(value)
