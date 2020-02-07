# example/schemas.py

from marshmallow import Schema, fields


class AuthorSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.String(required=True)
    created_at = fields.DateTime(dump_only=True)


class BookSchema(Schema):
    id = fields.Int(dump_only=True)
    title = fields.String(required=True)
    author_id = fields.Int(required=True)
    published_at = fields.DateTime(required=True)
    created_at = fields.DateTime(dump_only=True)
