from flask_resty import RelatedItem
import pytest
from marshmallow import fields, Schema

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
    data, errors = single_schema.dump({
        'child': {
            'id': 1,
            'name': "Foo",
        },
    })

    assert data == {
        'child': {
            'id': '1',
            'name': "Foo",
        },
    }
    assert not errors


def test_dump_many(many_schema):
    data, errors = many_schema.dump({
        'children': [
            {
                'id': 1,
                'name': "Foo",
            },
            {
                'id': 2,
                'name': "Bar",
            },
        ],
    })

    assert data == {
        'children': [
            {
                'id': '1',
                'name': "Foo",
            },
            {
                'id': '2',
                'name': "Bar",
            },
        ],
    }
    assert not errors


def test_load_single(single_schema):
    data, errors = single_schema.load({
        'child': {
            'id': '1',
        },
    })

    assert data == {
        'child': {
            'id': 1,
        },
    }
    assert not errors


def test_load_many(many_schema):
    data, errors = many_schema.load({
        'children': [
            {
                'id': '1',
            },
            {
                'id': '2',
            },
        ],
    })

    assert data == {
        'children': [
            {
                'id': 1,
            },
            {
                'id': 2,
            },
        ],
    }
    assert not errors


# -----------------------------------------------------------------------------


def test_error_load_single_missing(single_schema, error_messages):
    data, errors = single_schema.load({})

    assert not data
    assert errors == {
        'child': [error_messages['required']],
    }


def test_error_load_single_field_type(single_schema):
    data, errors = single_schema.load({
        'child': {
            'id': 'foo',
        },
    })

    assert not data
    assert errors == {
        'child': {
            'id': [fields.Integer().error_messages['invalid']],
        },
    }


def test_error_load_many_missing(many_schema, error_messages):
    data, errors = many_schema.load({})

    assert not data
    assert errors == {
        'children': [error_messages['required']],
    }


def test_error_load_many_type(many_schema, error_messages):
    data, errors = many_schema.load({
        'children': {
            'id': 1,
        },
    })

    assert not data
    assert errors == {
        'children': [error_messages['type']],
    }
