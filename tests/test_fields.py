import pytest
from marshmallow import Schema, ValidationError, fields

from flask_resty import RelatedItem
from flask_resty.compat import schema_dump, schema_load

# -----------------------------------------------------------------------------


@pytest.fixture
def related_schema_class():
    class RelatedSchema(Schema):
        id = fields.Integer(as_string=True)
        name = fields.String(required=True)

    return RelatedSchema


@pytest.fixture
def single_schema(related_schema_class):
    class SingleSchema(Schema):
        child = RelatedItem(related_schema_class, required=True)

    return SingleSchema()


@pytest.fixture
def many_schema(related_schema_class):
    class ManySchema(Schema):
        children = RelatedItem(related_schema_class, many=True, required=True)

    return ManySchema()


@pytest.fixture
def error_messages():
    return RelatedItem(None).error_messages


# -----------------------------------------------------------------------------


def test_dump_single(single_schema):
    data = schema_dump(single_schema, {"child": {"id": 1, "name": "Foo"}})

    assert data == {"child": {"id": "1", "name": "Foo"}}


def test_dump_many(many_schema):
    data = schema_dump(
        many_schema,
        {"children": [{"id": 1, "name": "Foo"}, {"id": 2, "name": "Bar"}]},
    )

    assert data == {
        "children": [{"id": "1", "name": "Foo"}, {"id": "2", "name": "Bar"}]
    }


def test_load_single(single_schema):
    data = schema_load(single_schema, {"child": {"id": "1"}})

    assert data == {"child": {"id": 1}}


def test_load_many(many_schema):
    data = schema_load(many_schema, {"children": [{"id": "1"}, {"id": "2"}]})

    assert data == {"children": [{"id": 1}, {"id": 2}]}


# -----------------------------------------------------------------------------


def test_error_load_single_missing(single_schema, error_messages):
    with pytest.raises(ValidationError) as excinfo:
        schema_load(single_schema, {})

    errors = excinfo.value.messages
    assert errors == {"child": [error_messages["required"]]}


def test_error_load_single_field_type(single_schema):
    with pytest.raises(ValidationError) as excinfo:
        schema_load(single_schema, {"child": {"id": "foo"}})

    errors = excinfo.value.messages
    assert errors == {
        "child": {"id": [fields.Integer().error_messages["invalid"]]}
    }


def test_error_load_many_missing(many_schema, error_messages):
    with pytest.raises(ValidationError) as excinfo:
        schema_load(many_schema, {})

    errors = excinfo.value.messages
    assert errors == {"children": [error_messages["required"]]}


def test_error_load_many_type(many_schema, error_messages):
    with pytest.raises(ValidationError) as excinfo:
        schema_load(many_schema, {"children": {"id": 1}})

    errors = excinfo.value.messages
    assert errors == {"children": [error_messages["type"]]}
