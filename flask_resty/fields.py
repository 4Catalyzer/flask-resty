from marshmallow import ValidationError
from marshmallow.fields import Field

__all__ = ('StubObject',)

# -----------------------------------------------------------------------------


class StubObject(Field):
    def _serialize(self, value, attr, obj):
        if value is None:
            return None

        return {
            'id': value,
        }

    def _deserialize(self, value, attr, data):
        try:
            id = value['id']
        except (TypeError, KeyError):
            raise ValidationError("incorrect input shape")
        else:
            return id
