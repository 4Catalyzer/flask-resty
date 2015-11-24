from flask.ext.resty import Api, GenericModelView, JsonApiSchema
import json
from marshmallow import fields
import pytest
from sqlalchemy import Column, Integer, String

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
    class WidgetSchema(JsonApiSchema):
        class Meta(object):
            type = 'widget'

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

    api = Api(app, '/api')
    api.add_resource(
        '/widgets', WidgetListView, WidgetView, id_rule='<int:id>'
    )


@pytest.fixture(autouse=True)
def data(db, models):
    def create_widget(name, description):
        widget = models['widget']()
        widget.name = name
        widget.description = description
        return widget

    db.session.add_all((
        create_widget("Foo", "foo widget"),
        create_widget("Bar", "bar widget"),
        create_widget("Baz", "baz widget"),
    ))
    db.session.commit()


# -----------------------------------------------------------------------------


def test_list(client):
    response = client.get('/api/widgets')
    assert response.status_code == 200
    assert response.mimetype == 'application/json'

    items = json.loads(response.data)['data']
    assert items == [
        {
            'type': 'widget',
            'id': '1',
            'name': "Foo",
            'description': "foo widget",
        },
        {
            'type': 'widget',
            'id': '2',
            'name': "Bar",
            'description': "bar widget",
        },
        {
            'type': 'widget',
            'id': '3',
            'name': "Baz",
            'description': "baz widget",
        },
    ]


def test_retrieve(client):
    response = client.get('/api/widgets/1')
    assert response.status_code == 200
    assert response.mimetype == 'application/json'

    item = json.loads(response.data)['data']
    assert item == {
        'type': 'widget',
        'id': '1',
        'name': "Foo",
        'description': "foo widget",
    }


def test_create(client):
    response = client.post(
        '/api/widgets',
        content_type='application/json',
        data=json.dumps({
            'data': {
                'type': 'widget',
                'name': "Qux",
                'description': "qux widget",
            },
        }),
    )
    assert response.status_code == 201
    assert response.mimetype == 'application/json'
    assert response.headers['Location'] == 'http://localhost/api/widgets/4'

    item = json.loads(response.data)['data']
    assert item == {
        'type': 'widget',
        'id': '4',
        'name': "Qux",
        'description': "qux widget",
    }


def test_update(client):
    update_response = client.patch(
        '/api/widgets/1',
        content_type='application/json',
        data=json.dumps({
            'data': {
                'type': 'widget',
                'id': '1',
                'description': "updated description",
            },
        }),
    )
    assert update_response.status_code == 204

    retrieve_response = client.get('/api/widgets/1')
    assert retrieve_response.status_code == 200
    assert retrieve_response.mimetype == 'application/json'

    item = json.loads(retrieve_response.data)['data']
    assert item == {
        'type': 'widget',
        'id': '1',
        'name': "Foo",
        'description': "updated description",
    }


def test_destroy(client):
    destroy_response = client.delete('/api/widgets/1')
    assert destroy_response.status_code == 204

    retrieve_response = client.get('/api/widgets/1')
    assert retrieve_response.status_code == 404
