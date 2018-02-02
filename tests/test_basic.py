from marshmallow import fields, Schema
from mock import Mock
import pytest
from sqlalchemy import Column, Integer, String

from flask_resty import Api, GenericModelView
from flask_resty.testing import assert_response

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


@pytest.fixture
def view_action_spy():
    return Mock()


@pytest.fixture(autouse=True)
def routes(app, models, schemas, view_action_spy):
    class WidgetViewBase(GenericModelView):
        model = models['widget']
        schema = schemas['widget']

        def dispatch_request(self, *args, **kwargs):
            response = super(WidgetViewBase, self).dispatch_request(
                *args, **kwargs
            )
            view_action_spy(self.action)
            return response

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
        '/widgets', WidgetListView, WidgetView, id_rule='<int:id>',
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


def test_list(client, view_action_spy):
    response = client.get('/widgets')

    assert_response(response, 200, [
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
    ])

    view_action_spy.assert_called_once_with('list')


def test_retrieve(client, view_action_spy):
    response = client.get('/widgets/1')

    assert_response(response, 200, {
        'id': '1',
        'name': "Foo",
        'description': "foo widget",
    })

    view_action_spy.assert_called_once_with('retrieve')


def test_create(client, view_action_spy):
    response = client.post('/widgets', data={
        'name': "Qux",
        'description': "qux widget",
    })

    assert response.headers['Location'] == 'http://localhost/widgets/4'
    assert_response(response, 201, {
        'id': '4',
        'name': "Qux",
        'description': "qux widget",
    })

    view_action_spy.assert_called_once_with('create')


def test_update(client, view_action_spy):
    update_response = client.patch('/widgets/1', data={
        'id': '1',
        'description': "updated description",
    })
    assert_response(update_response, 204)

    view_action_spy.assert_called_once_with('update')

    retrieve_response = client.get('/widgets/1')
    assert_response(retrieve_response, 200, {
        'id': '1',
        'name': "Foo",
        'description': "updated description",
    })


def test_destroy(client, view_action_spy):
    destroy_response = client.delete('/widgets/1')
    assert_response(destroy_response, 204)

    view_action_spy.assert_called_once_with('destroy')

    retrieve_response = client.get('/widgets/1')

    assert_response(retrieve_response, 404)
