from marshmallow import fields, ValidationError
from marshmallow.compat import basestring

from .exceptions import IncorrectTypeError

__all__ = ('StubObject',)

# -----------------------------------------------------------------------------


class Type(fields.Field):
    _CHECK_ATTRIBUTE = False

    def _add_to_schema(self, field_name, schema):
        super(Type, self)._add_to_schema(field_name, schema)
        self._type = schema.opts.type

    def _serialize(self, value, attr, obj):
        return self._type

    def _deserialize(self, value, attr, data):
        if value != self._type:
            raise IncorrectTypeError(value, self._type)


# -----------------------------------------------------------------------------


class StubObject(fields.Field):
    def __init__(self, type, **kwargs):
        super(StubObject, self).__init__(**kwargs)
        self._type = type

    def _serialize(self, value, attr, obj):
        return {'type': self._type, 'id': value}

    def _deserialize(self, value, attr, data):
        try:
            if value['type'] != self._type:
                raise IncorrectTypeError(value['type'], self._type)
            if not isinstance(value['id'], basestring):
                raise ValidationError("incorrect id type")
        except (TypeError, KeyError):
            raise ValidationError("incorrect input shape")

        return value['id']
