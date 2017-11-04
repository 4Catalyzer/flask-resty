from marshmallow import fields, Schema
import pytest
from sqlalchemy import Column, Integer

from flask_resty import Api, GenericModelView
from flask_resty.testing import assert_response

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


def test_api_prefix(app, views, client, base_client):
    api = Api(app, '/api')
    api.add_resource('/widgets', views['widget_list'])

    response = client.get('/widgets')
    assert_response(response, 200, [{
        'id': '1',
    }])

    response = base_client.get('/api/widgets')
    assert_response(response, 200, [{
        'id': '1',
    }])


def test_create_client_id(app, views, client):
    api = Api(app)
    api.add_resource('/widgets', views['widget_list'], views['widget'])

    response = client.post('/widgets', data={
        'id': '100',
    })
    assert response.headers['Location'] == 'http://localhost/widgets/100'
    assert_response(response, 201, {
        'id': '100',
    })


def test_create_no_location(app, views, client):
    views['widget_list'].get_location = lambda self, item: None

    api = Api(app)
    api.add_resource('/widgets', views['widget_list'], views['widget'])

    response = client.post('/widgets', data={})
    assert 'Location' not in response.headers
    assert_response(response, 201, {
        'id': '2',
    })


def test_training_slash(app, views, client):
    api = Api(app)
    api.add_resource(
        '/widgets/', views['widget_list'], views['widget'], id_rule='<id>/',
    )

    response = client.post('/widgets/', data={
        'id': '100',
    })
    assert response.headers['Location'] == 'http://localhost/widgets/100/'

    assert_response(response, 201, {
        'id': '100',
    })

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

    assert_response(get_response, 200, {
        'id': '1',
    })

    post_response = client.post('/widgets', data={})
    assert post_response.headers['Location'] == 'http://localhost/widget/2'

    assert_response(post_response, 201, {
        'id': '2',
    })


def test_factory_pattern(app, views, client):
    api = Api()
    api.init_app(app)

    with pytest.raises(AssertionError, message="no application specified"):
        api.add_resource('/widgets', views['widget_list'])

    api.add_resource('/widgets', views['widget_list'], app=app)

    response = client.get('/widgets')
    assert_response(response, 200, [{
        'id': '1',
    }])
