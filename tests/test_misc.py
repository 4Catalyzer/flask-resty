from flask_resty import Api, GenericModelView
from marshmallow import fields, Schema
import pytest
from sqlalchemy import Column, Integer

import helpers

# -----------------------------------------------------------------------------


@pytest.yield_fixture
def models(db):
    class Widget(db.Model):
        __tablename__ = 'widgets'

        id = Column(Integer, primary_key=True)

    db.create_all()

    yield {
        'widget': Widget,
    }

    db.drop_all()


@pytest.fixture
def schemas():
    class WidgetSchema(Schema):
        id = fields.Integer(as_string=True)

    return {
        'widget': WidgetSchema(),
    }


@pytest.fixture
def views(models, schemas):
    class WidgetViewBase(GenericModelView):
        model = models['widget']
        schema = schemas['widget']

    class WidgetListView(WidgetViewBase):
        def get(self):
            return self.list()

        def post(self):
            return self.create(allow_client_id=True)

    class WidgetView(WidgetViewBase):
        def get(self, id):
            return self.retrieve(id)

    return {
        'widget_list': WidgetListView,
        'widget': WidgetView,
    }


@pytest.fixture(autouse=True)
def data(db, models):
    db.session.add(models['widget']())
    db.session.commit()


# -----------------------------------------------------------------------------


def test_api_prefix(app, views, client):
    api = Api(app, '/api')
    api.add_resource('/widgets', views['widget_list'])

    response = client.get('/api/widgets')
    assert helpers.get_data(response) == [
        {
            'id': '1',
        },
    ]


def test_create_client_id(app, views, client):
    api = Api(app)
    api.add_resource('/widgets', views['widget_list'], views['widget'])

    response = helpers.request(
        client,
        'POST', '/widgets',
        {
            'id': '100',
        },
    )
    assert response.status_code == 201
    assert response.headers['Location'] == 'http://localhost/widgets/100'

    assert helpers.get_data(response) == {
        'id': '100',
    }


def test_training_slash(app, views, client):
    api = Api(app)
    api.add_resource(
        '/widgets/', views['widget_list'], views['widget'], id_rule='<id>/')

    response = helpers.request(
        client,
        'POST', '/widgets/',
        {
            'id': '100',
        },
    )
    assert response.status_code == 201
    assert response.headers['Location'] == 'http://localhost/widgets/100/'

    assert helpers.get_data(response) == {
        'id': '100',
    }
    response = client.get('/widgets/100/')
    assert response.status_code == 200


def test_resource_rules(app, views, client):
    api = Api(app)
    api.add_resource(
        base_rule='/widget/<id>',
        base_view=views['widget'],
        alternate_rule='/widgets',
        alternate_view=views['widget_list'],
    )

    get_response = client.get('/widget/1')
    assert get_response.status_code == 200

    assert helpers.get_data(get_response) == {
        'id': '1',
    }

    post_response = helpers.request(
        client,
        'POST', '/widgets',
        {},
    )
    assert post_response.status_code == 201
    assert post_response.headers['Location'] == 'http://localhost/widget/2'

    assert helpers.get_data(post_response) == {
        'id': '2',
    }
