import operator

from apispec import APISpec
from marshmallow import fields, Schema
import pytest

from flask_resty import (
    Api, Filtering, GenericModelView, PagePagination, Sorting,
    IdCursorPagination,
)
from flask_resty.spec import ModelViewDeclaration


# -----------------------------------------------------------------------------


@pytest.fixture()
def schemas(app):
    class FooSchema(Schema):
        id = fields.Integer(as_string=True)
        name = fields.String(required=True)
        color = fields.String()

    return {
        'foo': FooSchema
    }


@pytest.fixture(autouse=True)
def routes(app, schemas):
    class FooView(GenericModelView):
        schema = schemas['foo']()

        def get(self, id):
            pass

        def put(self, id):
            pass

        def delete(self, id):
            pass

        def patch(self):
            pass

    class FooListView(GenericModelView):
        schema = schemas['foo']()
        pagination = PagePagination(2)
        sorting = Sorting('name', 'color')
        spec_declaration = ModelViewDeclaration(many=True)

        filtering = Filtering(
            color=operator.eq,
        )

        def get(self):
            pass

        def post(self):
            """test the docstring"""
            pass

    class BarView(GenericModelView):
        pagination = IdCursorPagination(2)

        spec_declaration = ModelViewDeclaration(
            post={'204': {'description': 'request the creation of a new bar'}},
            get={'200': {}}
        )

        def post(self):
            pass

        def get(self):
            pass

        def put(self):
            """put a bar"""
            pass

    api = Api(app)
    api.add_resource('/foos', FooListView, FooView)
    api.add_resource('/bars', BarView)

    return {
        'foo': FooView,
        'fooList': FooListView,
        'bar': BarView,
    }


@pytest.fixture(autouse=True)
def ctx(app):
    ctx = app.test_request_context()
    ctx.push()


@pytest.fixture()
def spec(app, schemas, routes):
    spec = APISpec(
        title='test api',
        version='0.1.0',
        plugins=('apispec.ext.marshmallow', 'flask_resty.spec'))

    spec.definition('Foo', schema=schemas['foo'])

    spec.add_path(view=routes['fooList'])
    spec.add_path(view=routes['foo'])
    spec.add_path(view=routes['bar'])

    return spec.to_dict()

# -----------------------------------------------------------------------------


def test_definition_autogeneration(app, routes):
    spec = APISpec(
        title='test api',
        version='0.1.0',
        plugins=('apispec.ext.marshmallow', 'flask_resty.spec'))

    spec.add_path(view=routes['fooList'])

    assert 'FooSchema' in spec.to_dict()['definitions']


def test_tagging(app, routes):
    spec = APISpec(
        title='test api',
        version='0.1.0',
        plugins=('apispec.ext.marshmallow', 'flask_resty.spec'))

    spec.add_path(view=routes['fooList'])

    assert 'FooSchema' in spec.to_dict()['paths']['/foos']['get']['tags']


def test_invalid_kwargs():
    with pytest.raises(TypeError) as excinfo:
        ModelViewDeclaration(putt=123)
    assert 'invalid keyword argument "putt"' == str(excinfo.value)


def test_schema_definitions(spec):
    assert spec['definitions']['Foo'] == {
        'type': 'object',
        'required': ['name'],
        'properties': {
            'id': {'type': 'integer', 'format': 'int32'},
            'name': {'type': 'string'},
            'color': {'type': 'string'},
        }
    }


def test_paths(spec):
    assert '/foos' in spec['paths']
    assert '/foos/{id}' in spec['paths']
    assert '/bars' in spec['paths']


def test_get_response(spec):
    foo_get = spec['paths']['/foos/{id}']['get']
    assert foo_get['responses'] == {
        '200': {
            'description': '',
            'schema': {
                'type': 'object',
                'properties': {
                    'data': {'$ref': '#/definitions/Foo'}
                }
            }
        }
    }


def test_get_list_response(spec):
    foos_get = spec['paths']['/foos']['get']
    assert foos_get['responses']['200']['schema']['properties']['data'] == {
        'type': 'array',
        'items': {'$ref': '#/definitions/Foo'}
    }


def test_get_pagination_meta(spec):
    foos_get = spec['paths']['/foos']['get']
    assert foos_get['responses']['200']['schema']['properties']['meta'] == {
        'type': 'object',
        'properties': {
            'has_next_page': {'type': 'boolean'}
        }
    }


def test_post_response(spec):
    foos_get = spec['paths']['/foos']['post']
    assert foos_get['responses'] == {
        '201': {'description': ''}
    }


def test_put_response(spec):
    foo_put = spec['paths']['/foos/{id}']['put']
    assert foo_put['responses'] == {
        '204': {'description': ''}
    }


def test_delete_response(spec):
    foo_delete = spec['paths']['/foos/{id}']['delete']
    assert foo_delete['responses'] == {
        '204': {'description': ''}
    }


def test_only_requested_methods(spec):
    assert set(spec['paths']['/foos'].keys()) == {'post', 'get'}
    assert set(spec['paths']['/foos/{id}'].keys()) == \
        {'put', 'patch', 'delete', 'parameters', 'get'}
    assert set(spec['paths']['/bars'].keys()) == {'put', 'post', 'get'}


def test_path_params(spec):
    query_param = {
        'in': 'path',
        'required': True,
        'type': 'string',
        'name': 'id',
    }
    assert query_param in spec['paths']['/foos/{id}']['parameters']


def test_body_params(spec):
    foo_post = spec['paths']['/foos']['post']
    body = {
        'in': 'body',
        'name': 'body',
        'required': True,
        'schema': {'$ref': '#/definitions/Foo'}
    }
    assert body in foo_post['parameters']


def test_pagination(spec):
    foos_get = spec['paths']['/foos']['get']

    pars = [('limit', 'pagination limit'),
            ('offset', 'pagination offset'),
            ('page', 'page number')]

    for parameter_name, description in pars:
        parameter = {
            'in': 'query',
            'name': parameter_name,
            'type': 'int',
            'description': description,
        }
        assert parameter in foos_get['parameters']


def test_sorting(spec):
    foos_get = spec['paths']['/foos']['get']

    parameter = {
        'in': 'query',
        'name': 'sort',
        'type': 'string',
        'description': 'field to sort by',
    }
    assert parameter in foos_get['parameters']


def test_filters(spec):
    foos_get = spec['paths']['/foos']['get']

    parameter = {
        'in': 'query',
        'name': 'color',
        'type': 'string'
    }
    assert parameter in foos_get['parameters']


def test_docstring(spec):
    foos_post = spec['paths']['/foos']['post']
    assert foos_post['description'] == 'test the docstring'


def test_schemaless(spec):
    bars_post = spec['paths']['/bars']['post']
    assert bars_post['responses'] == {
        '204': {
            'description': 'request the creation of a new bar'
        }
    }

    bars_put = spec['paths']['/bars']['put']
    assert bars_put == {
        'responses': {},
        'parameters': [],
        'description': 'put a bar'
    }


def test_cursor_pagination(spec):
    bars_get = spec['paths']['/bars']['get']

    parameter = {
        'in': 'query',
        'name': 'cursor',
        'type': 'string',
        'description': 'pagination cursor',
    }
    assert parameter in bars_get['parameters']
