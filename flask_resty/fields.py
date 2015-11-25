from marshmallow import fields
from werkzeug import cached_property

# -----------------------------------------------------------------------------


class RelatedItem(fields.Nested):
    class SchemaProxy(object):
        def __init__(self, schema):
            self._schema = schema

        def load(self, *args, **kwargs):
            kwargs['partial'] = True
            return self._schema.load(*args, **kwargs)

        def __getattr__(self, item):
            return getattr(self._schema, item)

    @cached_property
    def schema(self):
        # Proxy the schema to always do partial loads.
        return self.SchemaProxy(super(RelatedItem, self).schema)
