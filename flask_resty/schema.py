from marshmallow import post_dump, post_load, pre_load, Schema, SchemaOpts

from .fields import Type
from . import utils

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

        if 'id' not in self.fields:
            raise ValueError("JSON API schemas must have an id")

    @post_dump
    def render_keys(self, data):
        render_key = utils.current_api.render_key
        return {render_key(key): value for key, value in data.items()}

    @pre_load
    def parse_keys(self, data):
        try:
            items = data.items()
        except AttributeError:
            # Let the unmarshaller handle this invalid input.
            return

        parse_key = utils.current_api.parse_key
        return {parse_key(key): value for key, value in items}

    @post_load
    def remove_type(self, data):
        # Type is specific to JSON API - it's not part of the model.
        del data['type']
