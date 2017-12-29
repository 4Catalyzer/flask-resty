from marshmallow import fields, Schema
import pytest

from flask_resty import Api, ApiView
from flask_resty.testing import assert_response

# -----------------------------------------------------------------------------


@pytest.fixture
def schemas():
    class NameSchema(Schema):
        name = fields.String(required=True)

    class NameListSchema(Schema):
        names = fields.List(fields.String(), load_from='name', required=True)

    class NameDefaultSchema(Schema):
        name = fields.String(required=True, missing='foo')

    return {
        'name': NameSchema(),
        'name_list': NameListSchema(),
        'name_default': NameDefaultSchema(),
    }


@pytest.fixture(autouse=True)
def routes(app, schemas):
    class NameView(ApiView):
        args_schema = schemas['name']

        def get(self):
            return self.make_response(self.get_request_args()['name'])

    class NameListView(ApiView):
        args_schema = schemas['name_list']

        def get(self):
            return self.make_response(self.get_request_args()['names'])

    class NameDefaultView(ApiView):
        args_schema = schemas['name_default']

        def get(self):
            return self.make_response(self.get_request_args()['name'])

    api = Api(app)
    api.add_resource('/name', NameView)
    api.add_resource('/names', NameListView)
    api.add_resource('/name_default', NameDefaultView)


# -----------------------------------------------------------------------------


def test_get_name_one(client):
    response = client.get('/name?name=foo')
    assert_response(response, 200, 'foo')


def test_get_name_extra(client):
    response = client.get('/name?name=foo&ignored=bar')
    assert_response(response, 200, 'foo')


def test_get_names_one(client):
    response = client.get('/names?name=foo')
    assert_response(response, 200, ['foo'])


def test_get_names_many(client):
    response = client.get('/names?name=foo&name=bar')
    assert_response(response, 200, ['foo', 'bar'])


def test_get_name_default(client):
    response = client.get('/name_default')
    assert_response(response, 200, 'foo')


def test_get_name_default_specified(client):
    response = client.get('/name_default?name=bar')
    assert_response(response, 200, 'bar')


# -----------------------------------------------------------------------------


def test_error_get_name_missing(client):
    response = client.get('/name')
    assert_response(response, 422, [{
        'code': 'invalid_parameter',
        'source': {'parameter': 'name'},
    }])


def test_error_get_name_many(client):
    response = client.get('/name?name=foo&name=bar')
    assert_response(response, 422, [{
        'code': 'invalid_parameter',
        'source': {'parameter': 'name'},
    }])


def test_error_get_names_missing(client):
    response = client.get('/names')
    assert_response(response, 422, [{
        'code': 'invalid_parameter',
        'source': {'parameter': 'name'},
    }])
