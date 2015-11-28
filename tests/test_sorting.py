from flask.ext.resty import Api, FixedSorting, GenericModelView, Sorting
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
        name = Column(String)
        size = Column(Integer)

    db.create_all()

    yield {
        'widget': Widget,
    }

    db.drop_all()


@pytest.fixture
def schemas():
    class WidgetSchema(Schema):
        id = fields.Integer(as_string=True)
        name = fields.String()
        size = fields.Integer()

    return {
        'widget': WidgetSchema(),
    }


@pytest.fixture(autouse=True)
def routes(app, models, schemas):
    class WidgetListView(GenericModelView):
        model = models['widget']
        schema = schemas['widget']

        sorting = Sorting('name', 'size')

        def get(self):
            return self.list()

    class FixedWidgetListView(WidgetListView):
        sorting = FixedSorting('name,size')

        def get(self):
            return self.list()

    api = Api(app)
    api.add_resource('/widgets', WidgetListView)
    api.add_resource('/fixed_widgets', FixedWidgetListView)


@pytest.fixture(autouse=True)
def data(db, models):
    def create_widget(name, size):
        widget = models['widget']()
        widget.name = name
        widget.size = size
        return widget

    db.session.add_all((
        create_widget("Foo", 1),
        create_widget("Foo", 5),
        create_widget("Baz", 3),
    ))
    db.session.commit()


# -----------------------------------------------------------------------------


def test_single(client):
    response = client.get('/widgets?sort=size')

    assert helpers.get_data(response) == [
        {
            'id': '1',
            'name': "Foo",
            'size': 1,
        },
        {
            'id': '3',
            'name': "Baz",
            'size': 3,
        },
        {
            'id': '2',
            'name': "Foo",
            'size': 5,
        },
    ]


def test_many(client):
    response = client.get('/widgets?sort=name,-size')

    assert helpers.get_data(response) == [
        {
            'id': '3',
            'name': "Baz",
            'size': 3,
        },
        {
            'id': '2',
            'name': "Foo",
            'size': 5,
        },
        {
            'id': '1',
            'name': "Foo",
            'size': 1,
        },
    ]


def test_no_sort(client):
    response = client.get('/widgets')

    assert helpers.get_data(response) == [
        {
            'id': '1',
            'name': "Foo",
            'size': 1,
        },
        {
            'id': '2',
            'name': "Foo",
            'size': 5,
        },
        {
            'id': '3',
            'name': "Baz",
            'size': 3,
        },
    ]


def test_fixed(client):
    response = client.get('/fixed_widgets')

    assert helpers.get_data(response) == [
        {
            'id': '3',
            'name': "Baz",
            'size': 3,
        },
        {
            'id': '1',
            'name': "Foo",
            'size': 1,
        },
        {
            'id': '2',
            'name': "Foo",
            'size': 5,
        },
    ]


# -----------------------------------------------------------------------------


def test_error_invalid_field(client):
    response = client.get('/widgets?sort=id')
    assert response.status_code == 400

    assert helpers.get_errors(response) == [{
        'code': 'invalid_sort',
        'source': {'parameter': 'sort'},
    }]


def test_error_empty(client):
    response = client.get('/widgets?sort=')
    assert response.status_code == 400

    assert helpers.get_errors(response) == [{
        'code': 'invalid_sort',
        'source': {'parameter': 'sort'},
    }]
