from marshmallow import Schema, SchemaOpts

__all__ = ('JsonApiSchema',)

# -----------------------------------------------------------------------------


class JsonApiSchemaOpts(SchemaOpts):
    def __init__(self, meta):
        super(JsonApiSchemaOpts, self).__init__(meta)

        self.type = getattr(meta, 'type', None)

        # Override base default to strict validation instead.
        self.strict = getattr(meta, 'strict', True)


class JsonApiSchema(Schema):
    OPTIONS_CLASS = JsonApiSchemaOpts

    def __init__(self, *args, **kwargs):
        super(JsonApiSchema, self).__init__(*args, **kwargs)

        self.extra = self.extra or {}
        self.extra['type'] = self.opts.type
