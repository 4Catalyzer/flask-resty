from flask_resty import Api, GenericModelView
from marshmallow import fields, Schema
import pytest
from sqlalchemy import Column, Integer, String

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
            'nested_many': [
                {'value': 'four'},
                {'value': 5},
                {'value': 'six'},
            ],
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


def test_commit_conflict(client):
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
