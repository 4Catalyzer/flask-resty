from flask_resty import Api, GenericModelView
from marshmallow import fields, Schema
from mock import PropertyMock
import pytest
from sqlalchemy import Column, Integer, String
from sqlalchemy.exc import DataError

import helpers

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
    widget = models['widget']()
    widget.name = "Foo"

    db.session.add(widget)
    db.session.commit()


# -----------------------------------------------------------------------------


def test_invalid_body(client):
    response = client.post(
        '/widgets',
        data='foo',
    )
    assert response.status_code == 400

    assert helpers.get_errors(response) == [{
        'code': 'invalid_body',
    }]


def test_data_missing(client):
    response = client.post(
        '/widgets',
        content_type='application/json',
        data='{}',
    )
    assert response.status_code == 400

    assert helpers.get_errors(response) == [{
        'code': 'invalid_data.missing',
    }]


def test_deserializer_errors(client):
    response = helpers.request(
        client,
        'POST', '/widgets',
        {
            'nested': {'value': 'three'},
        },
    )
    assert response.status_code == 422

    errors = helpers.get_errors(response)
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
    ]


def test_id_forbidden(client):
    response = helpers.request(
        client,
        'POST', '/widgets',
        {
            'id': '2',
            'name': "Bar",
        },
    )
    assert response.status_code == 403

    assert helpers.get_errors(response) == [{
        'code': 'invalid_id.forbidden',
    }]


def test_id_missing(client):
    response = helpers.request(
        client,
        'PATCH', '/widgets/1',
        {
            'name': "Bar",
        },
    )
    assert response.status_code == 422

    assert helpers.get_errors(response) == [{
        'code': 'invalid_id.missing',
    }]


def test_id_mismatch(client):
    response = helpers.request(
        client,
        'PATCH', '/widgets/1',
        {
            'id': '2',
            'name': "Bar",
        },
    )
    assert response.status_code == 409

    assert helpers.get_errors(response) == [{
        'code': 'invalid_id.mismatch',
    }]


def test_invalid_id(views, client):
    # Normally the DataError might come from a type error, but SQLite is
    # dynamically typed, so it's easier to trigger one with a mock.
    views['widget'].query = PropertyMock(
        side_effect=DataError(None, None, None),
    )

    response = client.get('/widgets/1')
    assert response.status_code == 400


def test_commit_integrity_error(client):
    response = helpers.request(
        client,
        'POST', '/widgets',
        {
            'name': "Foo",
        },
    )
    assert response.status_code == 409

    assert helpers.get_errors(response) == [{
        'code': 'invalid_data.conflict',
    }]


def test_commit_data_error(views, client):
    # Normally the DataError might come from a type error, but SQLite is
    # dynamically typed, so it's easier to trigger one with a mock.
    views['widget'].session = PropertyMock(
        side_effect=DataError(None, None, None),
    )

    response = helpers.request(
        client,
        'PATCH', '/widgets/1',
        {
            'id': '1',
            'name': "Bar",
        },
    )
    assert response.status_code == 422

    assert helpers.get_errors(response) == [{
        'code': 'invalid_data',
    }]


def test_debug(app, client):
    production_response = client.post(
        '/widgets',
        data='foo',
    )
    assert production_response.status_code == 400
    assert 'debug' not in helpers.get_body(production_response)

    app.debug = True
    debug_response = client.post(
        '/widgets',
        data='foo',
    )
    assert debug_response.status_code == 400
    assert 'debug' in helpers.get_body(debug_response)
