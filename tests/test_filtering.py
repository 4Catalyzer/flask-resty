import operator

from marshmallow import fields, Schema
import pytest
from sqlalchemy import Column, Integer, sql, String

from flask_resty import Api, filter_function, Filtering, GenericModelView
from flask_resty.testing import assert_response

# -----------------------------------------------------------------------------


@pytest.yield_fixture
def models(db):
    class Widget(db.Model):
        __tablename__ = 'widgets'

        id = Column(Integer, primary_key=True)
        color = Column(String)
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
        color = fields.String()
        size = fields.Integer()

    return {
        'widget': WidgetSchema(),
    }


@pytest.fixture
def filter_fields():
    @filter_function(fields.Boolean())
    def filter_size_is_odd(model, value):
        return model.size % 2 == int(value)

    @filter_function(fields.String(), separator=None)
    def filter_color_no_separator(model, value):
        return model.color == value

    return {
        'size_is_odd': filter_size_is_odd,
        'color_no_separator': filter_color_no_separator,
    }


@pytest.fixture(autouse=True)
def routes(app, models, schemas, filter_fields):
    class WidgetListView(GenericModelView):
        model = models['widget']
        schema = schemas['widget']

        filtering = Filtering(
            color=operator.eq,
            size=(operator.eq, {
                'separator': '|',
                'empty': sql.false(),
            }),
            size_alt=(operator.eq, {
                'empty': lambda view: view.model.size == 1,
            }),
            size_min=('size', operator.ge),
            size_divides=('size', lambda size, value: size % value == 0),
            size_is_odd=filter_fields['size_is_odd'],
            color_no_separator=filter_fields['color_no_separator'],
        )

        def get(self):
            return self.list()

    api = Api(app)
    api.add_resource('/widgets', WidgetListView)


@pytest.fixture(autouse=True)
def data(db, models):
    db.session.add_all((
        models['widget'](color='red', size=1),
        models['widget'](color='green', size=2),
        models['widget'](color='blue', size=3),
        models['widget'](color='red', size=6),
    ))
    db.session.commit()


# -----------------------------------------------------------------------------


def test_eq(client):
    response = client.get('/widgets?color=red')
    assert_response(response, 200, [
        {
            'id': '1',
            'color': 'red',
            'size': 1,
        },
        {
            'id': '4',
            'color': 'red',
            'size': 6,
        },
    ])


def test_eq_many(client):
    response = client.get('/widgets?color=green,blue')
    assert_response(response, 200, [
        {
            'id': '2',
            'color': 'green',
            'size': 2,
        },
        {
            'id': '3',
            'color': 'blue',
            'size': 3,
        },
    ])


def test_eq_many_custom_separator(client):
    response = client.get('/widgets?size=2|3')
    assert_response(response, 200, [
        {
            'id': '2',
            'color': 'green',
            'size': 2,
        },
        {
            'id': '3',
            'color': 'blue',
            'size': 3,
        },
    ])


def test_eq_empty(client):
    response = client.get('/widgets?color=')
    assert_response(response, 200, [])


def test_eq_empty_custom_column_element(client):
    response = client.get('/widgets?size=')
    assert_response(response, 200, [])


def test_eq_empty_custom_function(client):
    response = client.get('/widgets?size_alt=')
    assert_response(response, 200, [
        {
            'id': '1',
            'color': 'red',
            'size': 1,
        },
    ])


def test_ge(client):
    response = client.get('/widgets?size_min=3')
    assert_response(response, 200, [
        {
            'id': '3',
            'color': 'blue',
            'size': 3,
        },
        {
            'id': '4',
            'color': 'red',
            'size': 6,
        },
    ])


def test_custom_operator(client):
    response = client.get('/widgets?size_divides=2')
    assert_response(response, 200, [
        {
            'id': '2',
            'color': 'green',
            'size': 2,
        },
        {
            'id': '4',
            'color': 'red',
            'size': 6,
        },
    ])


def test_filter_field(client):
    response = client.get('/widgets?size_is_odd=true')
    assert_response(response, 200, [
        {
            'id': '1',
            'color': 'red',
            'size': 1,
        },
        {
            'id': '3',
            'color': 'blue',
            'size': 3,
        },
    ])


def test_filter_field_kwargs(client):
    red_response = client.get('/widgets?color_no_separator=red')
    assert_response(red_response, 200, [
        {
            'id': '1',
            'color': 'red',
            'size': 1,
        },
        {
            'id': '4',
            'color': 'red',
            'size': 6,
        },
    ])

    empty_response = client.get('/widgets?color_no_separator=red,blue')
    assert_response(empty_response, 200, [])


# -----------------------------------------------------------------------------


def test_error_invalid_field(client):
    response = client.get('/widgets?size_min=foo')
    assert_response(response, 400, [{
        'code': 'invalid_filter',
        'detail': 'Not a valid integer.',
        'source': {'query': 'size_min'},
    }])
