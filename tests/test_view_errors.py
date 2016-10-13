from flask_resty import Api, GenericModelView
from flask_resty.testing import assert_response, get_body, get_errors
from marshmallow import fields, Schema
import pytest
from sqlalchemy import Column, Integer, String

from helpers import request

# -----------------------------------------------------------------------------


@pytest.yield_fixture
def models(db):
    class Widget(db.Model):
        __tablename__ = 'widgets'

        id = Column(Integer, primary_key=True)
        name = Column(String, nullable=False, unique=True)

    db.create_all()

    yield {
        'widget': Widget,
    }

    db.drop_all()


@pytest.fixture
def schemas():
    class NestedSchema(Schema):
        value = fields.Integer()

    class WidgetSchema(Schema):
        id = fields.Integer(as_string=True)
        name = fields.String(required=True)
        nested = fields.Nested(NestedSchema)
        nested_many = fields.Nested(NestedSchema, many=True)

    return {
        'widget': WidgetSchema(),
    }


@pytest.fixture
def views(models, schemas):
    class WidgetViewBase(GenericModelView):
        model = models['widget']
        schema = schemas['widget']

    class WidgetListView(WidgetViewBase):
        def post(self):
            return self.create()

    class WidgetView(WidgetViewBase):
        def get(self, id):
            return self.retrieve(id)

        def patch(self, id):
            return self.update(id, partial=True)

    return {
        'widget_list': WidgetListView,
        'widget': WidgetView,
    }


@pytest.fixture(autouse=True)
def routes(app, views):
    api = Api(app)
    api.add_resource(
        '/widgets', views['widget_list'], views['widget'], id_rule='<int:id>'
    )


@pytest.fixture(autouse=True)
def data(db, models):
    db.session.add(models['widget'](name="Foo"))
    db.session.commit()


# -----------------------------------------------------------------------------


def test_invalid_body(client):
    response = client.post(
        '/widgets',
        data='foo',
    )
    assert_response(response, 400, [{
        'code': 'invalid_body',
    }])


def test_data_missing(client):
    response = client.post(
        '/widgets',
        content_type='application/json',
        data='{}',
    )
    assert_response(response, 400, [{
        'code': 'invalid_data.missing',
    }])


def test_deserializer_errors(client):
    response = request(
        client,
        'POST', '/widgets',
        {
            'nested': {'value': 'three'},
            'nested_many': [
                {'value': 'four'},
                {'value': 5},
                {'value': 'six'},
            ],
        },
    )
    assert_response(response, 422)

    errors = get_errors(response)
    for error in errors:
        assert error.pop('detail', None) is not None

    errors.sort(key=lambda error: error['source']['pointer'])
    assert errors == [
        {
            'code': 'invalid_data',
            'source': {'pointer': '/data/name'},
        },
        {
            'code': 'invalid_data',
            'source': {'pointer': '/data/nested/value'},
        },
        {
            'code': 'invalid_data',
            'source': {'pointer': '/data/nested_many/0/value'},
        },
        {
            'code': 'invalid_data',
            'source': {'pointer': '/data/nested_many/2/value'},
        },
    ]


def test_id_forbidden(client):
    response = request(
        client,
        'POST', '/widgets',
        {
            'id': '2',
            'name': "Bar",
        },
    )
    assert_response(response, 403, [{
        'code': 'invalid_id.forbidden',
    }])


def test_id_missing(client):
    response = request(
        client,
        'PATCH', '/widgets/1',
        {
            'name': "Bar",
        },
    )
    assert_response(response, 422, [{
        'code': 'invalid_id.missing',
    }])


def test_id_mismatch(client):
    response = request(
        client,
        'PATCH', '/widgets/1',
        {
            'id': '2',
            'name': "Bar",
        },
    )
    assert_response(response, 409, [{
        'code': 'invalid_id.mismatch',
    }])


def test_commit_conflict(client):
    response = request(
        client,
        'POST', '/widgets',
        {
            'name': "Foo",
        },
    )
    assert_response(response, 409, [{
        'code': 'invalid_data.conflict',
    }])


def test_debug(app, client):
    app.debug = False
    app.testing = False

    production_response = client.post(
        '/widgets',
        data='foo',
    )
    assert_response(production_response, 400)
    assert 'debug' not in get_body(production_response)

    app.debug = True
    app.testing = False

    debug_response = client.post(
        '/widgets',
        data='foo',
    )
    assert_response(debug_response, 400)
    assert 'debug' in get_body(debug_response)

    app.debug = False
    app.testing = True

    testing_response = client.post(
        '/widgets',
        data='foo',
    )
    assert_response(testing_response, 400)
    assert 'debug' in get_body(testing_response)
