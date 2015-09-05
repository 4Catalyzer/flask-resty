from marshmallow import post_load, Schema, SchemaOpts

from .fields import Type

__all__ = ('JsonApiSchema',)

# -----------------------------------------------------------------------------


class JsonApiSchemaOpts(SchemaOpts):
    def __init__(self, meta):
        super(JsonApiSchemaOpts, self).__init__(meta)

        self.type = getattr(meta, 'type', None)

        # Always use strict validation and catch exceptions.
        if not getattr(meta, 'strict', True):
            raise ValueError("JSON API schemas must be strict")
        self.strict = True


class JsonApiSchema(Schema):
    OPTIONS_CLASS = JsonApiSchemaOpts

    type = Type(required=True)

    def __init__(self, *args, **kwargs):
        super(JsonApiSchema, self).__init__(*args, **kwargs)

        if not self.opts.type:
            raise ValueError("JSON API schemas must specify a type")

    @post_load
    def remove_type(self, data):
        # Type is specific to JSON API - it's not part of the model.
        del data['type']
