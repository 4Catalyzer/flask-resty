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

        id_1 = Column(Integer, primary_key=True)
        id_2 = Column(Integer, primary_key=True)
        name = Column(String, nullable=False)

    db.create_all()

    yield {
        'widget': Widget,
    }

    db.drop_all()


@pytest.fixture
def schemas():
    class WidgetSchema(Schema):
        id_1 = fields.Integer(as_string=True)
        id_2 = fields.Integer(as_string=True)
        name = fields.String(required=True)

    return {
        'widget': WidgetSchema(),
    }


@pytest.fixture(autouse=True)
def routes(app, models, schemas):
    class WidgetViewBase(GenericModelView):
        model = models['widget']
        schema = schemas['widget']
        id_fields = ('id_1', 'id_2')

    class WidgetListView(WidgetViewBase):
        def get(self):
            return self.list()

        def post(self):
            return self.create(allow_client_id=True)

    class WidgetView(WidgetViewBase):
        def get(self, id_1, id_2):
            return self.retrieve((id_1, id_2))

        def patch(self, id_1, id_2):
            return self.update((id_1, id_2), partial=True)

        def delete(self, id_1, id_2):
            return self.destroy((id_1, id_2))

    api = Api(app)
    api.add_resource(
        '/widgets', WidgetListView, WidgetView,
        id_rule='<int:id_1>/<int:id_2>',
    )


@pytest.fixture(autouse=True)
def data(db, models):
    db.session.add_all((
        models['widget'](id_1=1, id_2=2, name="Foo"),
        models['widget'](id_1=1, id_2=3, name="Bar"),
        models['widget'](id_1=4, id_2=5, name="Baz"),
    ))
    db.session.commit()


# -----------------------------------------------------------------------------


def test_list(client):
    response = client.get('/widgets')
    assert response.status_code == 200

    assert helpers.get_data(response) == [
        {
            'id_1': '1',
            'id_2': '2',
            'name': "Foo",
        },
        {
            'id_1': '1',
            'id_2': '3',
            'name': "Bar",
        },
        {
            'id_1': '4',
            'id_2': '5',
            'name': "Baz",
        },
    ]


def test_retrieve(client):
    response = client.get('/widgets/1/2')
    assert response.status_code == 200

    assert helpers.get_data(response) == {
        'id_1': '1',
        'id_2': '2',
        'name': "Foo",
    }


def test_create(client):
    response = helpers.request(
        client,
        'POST', '/widgets',
        {
            'id_1': '4',
            'id_2': '6',
            'name': "Qux",
        },
    )
    assert response.status_code == 201
    assert response.headers['Location'] == 'http://localhost/widgets/4/6'

    assert helpers.get_data(response) == {
        'id_1': '4',
        'id_2': '6',
        'name': "Qux",
    }


def test_update(client):
    update_response = helpers.request(
        client,
        'PATCH', '/widgets/1/2',
        {
            'id_1': '1',
            'id_2': '2',
            'name': "Qux",
        },
    )
    assert update_response.status_code == 204

    retrieve_response = client.get('/widgets/1/2')
    assert retrieve_response.status_code == 200

    assert helpers.get_data(retrieve_response) == {
        'id_1': '1',
        'id_2': '2',
        'name': "Qux",
    }


def test_destroy(client):
    destroy_response = client.delete('/widgets/1/2')
    assert destroy_response.status_code == 204

    retrieve_response = client.get('/widgets/1/2')
    assert retrieve_response.status_code == 404
