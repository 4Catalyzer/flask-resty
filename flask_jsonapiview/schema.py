from marshmallow import (
    post_dump, post_load, pre_load, Schema, SchemaOpts, ValidationError
)
from marshmallow.compat import iteritems

from .fields import Type

__all__ = ('JsonApiSchema',)

# -----------------------------------------------------------------------------


class JsonApiSchemaOpts(SchemaOpts):
    def __init__(self, meta):
        super(JsonApiSchemaOpts, self).__init__(meta)

        self.type = getattr(meta, 'type', None)
        self.use_param_case = getattr(meta, 'use_param_case', True)

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
    def keys_to_param_case(self, data):
        if not self.opts.use_param_case:
            return

        return {
            self.to_param_case(key): value for key, value in iteritems(data)
        }

    def to_param_case(self, key):
        if '-' in key:
            raise ValueError("key {} not in snake case".format(key))

        return key.replace('_', '-')

    @pre_load
    def keys_from_param_case(self, data):
        if not self.opts.use_param_case:
            return

        try:
            items = iteritems(data)
        except AttributeError:
            # Let the unmarshaller handle this invalid input.
            return

        return {self.from_param_case(key): value for key, value in items}

    def from_param_case(self, key):
        if '_' in key:
            raise ValidationError("key {} not in param case".format(key))

        return key.replace('-', '_')

    @post_load
    def remove_type(self, data):
        # Type is specific to JSON API - it's not part of the model.
        del data['type']
