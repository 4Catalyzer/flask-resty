import pytest
from marshmallow import Schema, ValidationError, fields

from flask_resty.fields import DelimitedList, RelatedItem

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


@pytest.fixture
def delimited_list_schema():
    class DelimitedListSchema(Schema):
        ids = DelimitedList(fields.String, required=True)

    return DelimitedListSchema()


@pytest.fixture
def delimited_list_as_string_schema():
    class DelimitedListAsStringSchema(Schema):
        ids = DelimitedList(fields.String, as_string=True, required=True)

    return DelimitedListAsStringSchema()


# -----------------------------------------------------------------------------


def test_dump_single(single_schema):
    data = single_schema.dump({"child": {"id": 1, "name": "Foo"}})

    assert data == {"child": {"id": "1", "name": "Foo"}}


def test_dump_many(many_schema):
    data = many_schema.dump(
        {"children": [{"id": 1, "name": "Foo"}, {"id": 2, "name": "Bar"}]}
    )

    assert data == {
        "children": [{"id": "1", "name": "Foo"}, {"id": "2", "name": "Bar"}]
    }


def test_load_single(single_schema):
    data = single_schema.load({"child": {"id": "1"}})

    assert data == {"child": {"id": 1}}


def test_load_many(many_schema):
    data = many_schema.load({"children": [{"id": "1"}, {"id": "2"}]})

    assert data == {"children": [{"id": 1}, {"id": 2}]}


# -----------------------------------------------------------------------------


def test_error_load_single_missing(single_schema, error_messages):
    with pytest.raises(ValidationError) as excinfo:
        single_schema.load({})

    errors = excinfo.value.messages
    assert errors == {"child": [error_messages["required"]]}


def test_error_load_single_field_type(single_schema):
    with pytest.raises(ValidationError) as excinfo:
        single_schema.load({"child": {"id": "foo"}})

    errors = excinfo.value.messages
    assert errors == {
        "child": {"id": [fields.Integer().error_messages["invalid"]]}
    }


def test_error_load_many_missing(many_schema, error_messages):
    with pytest.raises(ValidationError) as excinfo:
        many_schema.load({})

    errors = excinfo.value.messages
    assert errors == {"children": [error_messages["required"]]}


def test_error_load_many_type(many_schema, error_messages):
    with pytest.raises(ValidationError) as excinfo:
        many_schema.load({"children": {"id": 1}})

    errors = excinfo.value.messages
    assert errors == {"children": [error_messages["type"]]}


# -----------------------------------------------------------------------------


def test_load_delimited_list(delimited_list_schema):
    data = delimited_list_schema.load({"ids": "1,2,3"})

    assert data == {"ids": ["1", "2", "3"]}


def test_dump_delimited_list(delimited_list_schema):
    data = delimited_list_schema.dump({"ids": ["1", "2", "3"]})

    assert data == {"ids": ["1", "2", "3"]}


def test_delimited_list_as_string(delimited_list_as_string_schema):
    data = delimited_list_as_string_schema.dump({"ids": ["1", "2", "3"]})

    assert data == {"ids": "1,2,3"}


# -----------------------------------------------------------------------------


def test_error_delimited_list_validation_error(delimited_list_schema):
    with pytest.raises(ValidationError) as excinfo:
        delimited_list_schema.load({"ids": 1})

    errors = excinfo.value.messages
    assert errors == {"ids": ["Not a valid list."]}
