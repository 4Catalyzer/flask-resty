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
        name = Column(String, nullable=False)
        description = Column(String)

    db.create_all()

    yield {
        'widget': Widget,
    }

    db.drop_all()


@pytest.fixture
def schemas():
    class WidgetSchema(Schema):
        id = fields.Integer(as_string=True)
        name = fields.String(required=True)
        description = fields.String()

    return {
        'widget': WidgetSchema(),
    }


@pytest.fixture(autouse=True)
def routes(app, models, schemas):
    class WidgetViewBase(GenericModelView):
        model = models['widget']
        schema = schemas['widget']

    class WidgetListView(WidgetViewBase):
        def get(self):
            return self.list()

        def post(self):
            return self.create()

    class WidgetView(WidgetViewBase):
        def get(self, id):
            return self.retrieve(id)

        def patch(self, id):
            return self.update(id, partial=True)

        def delete(self, id):
            return self.destroy(id)

    api = Api(app)
    api.add_resource(
        '/widgets', WidgetListView, WidgetView, id_rule='<int:id>'
    )


@pytest.fixture(autouse=True)
def data(db, models):
    db.session.add_all((
        models['widget'](name="Foo", description="foo widget"),
        models['widget'](name="Bar", description="bar widget"),
        models['widget'](name="Baz", description="baz widget"),
    ))
    db.session.commit()


# -----------------------------------------------------------------------------


def test_list(client):
    response = client.get('/widgets')
    assert response.status_code == 200

    assert helpers.get_data(response) == [
        {
            'id': '1',
            'name': "Foo",
            'description': "foo widget",
        },
        {
            'id': '2',
            'name': "Bar",
            'description': "bar widget",
        },
        {
            'id': '3',
            'name': "Baz",
            'description': "baz widget",
        },
    ]


def test_retrieve(client):
    response = client.get('/widgets/1')
    assert response.status_code == 200

    assert helpers.get_data(response) == {
        'id': '1',
        'name': "Foo",
        'description': "foo widget",
    }


def test_create(client):
    response = helpers.request(
        client,
        'POST', '/widgets',
        {
            'name': "Qux",
            'description': "qux widget",
        },
    )
    assert response.status_code == 201
    assert response.headers['Location'] == 'http://localhost/widgets/4'

    assert helpers.get_data(response) == {
        'id': '4',
        'name': "Qux",
        'description': "qux widget",
    }


def test_update(client):
    update_response = helpers.request(
        client,
        'PATCH', '/widgets/1',
        {
            'id': '1',
            'description': "updated description",
        },
    )
    assert update_response.status_code == 204

    retrieve_response = client.get('/widgets/1')
    assert retrieve_response.status_code == 200

    assert helpers.get_data(retrieve_response) == {
        'id': '1',
        'name': "Foo",
        'description': "updated description",
    }


def test_destroy(client):
    destroy_response = client.delete('/widgets/1')
    assert destroy_response.status_code == 204

    retrieve_response = client.get('/widgets/1')
    assert retrieve_response.status_code == 404
