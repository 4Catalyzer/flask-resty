from flask_resty import (
    Api, Filtering, GenericModelView, IdCursorPagination,
    LimitOffsetPagination, PagePagination, Sorting
)
from marshmallow import fields, Schema
import operator
import pytest
from sqlalchemy import Column, Integer

import helpers

# -----------------------------------------------------------------------------


@pytest.yield_fixture
def models(db):
    class Widget(db.Model):
        __tablename__ = 'widgets'

        id = Column(Integer, primary_key=True)
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
        size = fields.Integer()

    return {
        'widget': WidgetSchema(),
    }


@pytest.fixture(autouse=True)
def routes(app, models, schemas):
    class WidgetViewBase(GenericModelView):
        model = models['widget']
        schema = schemas['widget']

    class LimitOffsetWidgetListView(WidgetViewBase):
        filtering = Filtering(
            size=operator.eq,
        )
        pagination = LimitOffsetPagination(2, 4)

        def get(self):
            return self.list()

    class PageWidgetListView(WidgetViewBase):
        pagination = PagePagination(2)

        def get(self):
            return self.list()

    class IdCursorListView(WidgetViewBase):
        sorting = Sorting(
            'id', 'size',
            default='id',
        )
        pagination = IdCursorPagination(2)

        def get(self):
            return self.list()

    api = Api(app)
    api.add_resource('/limit_offset_widgets', LimitOffsetWidgetListView)
    api.add_resource('/page_widgets', PageWidgetListView)
    api.add_resource('/id_cursor_widgets', IdCursorListView)


@pytest.fixture(autouse=True)
def data(db, models):
    db.session.add_all((
        models['widget'](size=1),
        models['widget'](size=2),
        models['widget'](size=3),
        models['widget'](size=1),
        models['widget'](size=2),
        models['widget'](size=3),
    ))
    db.session.commit()


# -----------------------------------------------------------------------------


def test_limit_offset(client):
    response = client.get('/limit_offset_widgets?offset=2&limit=3')

    assert helpers.get_data(response) == [
        {
            'id': '3',
            'size': 3,
        },
        {
            'id': '4',
            'size': 1,
        },
        {
            'id': '5',
            'size': 2,
        },
    ]
    assert helpers.get_meta(response) == {
        'has_next_page': True
    }


def test_limit_offset_default(client):
    response = client.get('/limit_offset_widgets')

    assert helpers.get_data(response) == [
        {
            'id': '1',
            'size': 1,
        },
        {
            'id': '2',
            'size': 2,
        },
    ]
    assert helpers.get_meta(response) == {
        'has_next_page': True
    }


def test_limit_offset_limit(client):
    response = client.get('/limit_offset_widgets?limit=3')

    assert helpers.get_data(response) == [
        {
            'id': '1',
            'size': 1,
        },
        {
            'id': '2',
            'size': 2,
        },
        {
            'id': '3',
            'size': 3,
        },
    ]
    assert helpers.get_meta(response) == {
        'has_next_page': True
    }


def test_limit_offset_max_limit(client):
    response = client.get('/limit_offset_widgets?limit=5')

    assert helpers.get_data(response) == [
        {
            'id': '1',
            'size': 1,
        },
        {
            'id': '2',
            'size': 2,
        },
        {
            'id': '3',
            'size': 3,
        },
        {
            'id': '4',
            'size': 1,
        },
    ]
    assert helpers.get_meta(response) == {
        'has_next_page': True
    }


def test_limit_offset_offset(client):
    response = client.get('/limit_offset_widgets?offset=2')

    assert helpers.get_data(response) == [
        {
            'id': '3',
            'size': 3,
        },
        {
            'id': '4',
            'size': 1,
        },
    ]
    assert helpers.get_meta(response) == {
        'has_next_page': True
    }


def test_limit_offset_offset_end(client):
    response = client.get('/limit_offset_widgets?offset=4')

    assert helpers.get_data(response) == [
        {
            'id': '5',
            'size': 2,
        },
        {
            'id': '6',
            'size': 3,
        },
    ]
    assert helpers.get_meta(response) == {
        'has_next_page': False
    }


def test_limit_offset_offset_truncate(client):
    response = client.get('/limit_offset_widgets?offset=5')

    assert helpers.get_data(response) == [
        {
            'id': '6',
            'size': 3,
        },
    ]
    assert helpers.get_meta(response) == {
        'has_next_page': False
    }


def test_limit_offset_filtered(client):
    response = client.get('/limit_offset_widgets?size=2&limit=1')

    assert helpers.get_data(response) == [
        {
            'id': '2',
            'size': 2,
        },
    ]
    assert helpers.get_meta(response) == {
        'has_next_page': True
    }


def test_limit_offset_filtered_offset(client):
    response = client.get('/limit_offset_widgets?size=2&offset=1')

    assert helpers.get_data(response) == [
        {
            'id': '5',
            'size': 2,
        },
    ]
    assert helpers.get_meta(response) == {
        'has_next_page': False
    }


def test_page(client):
    response = client.get('/page_widgets?page=1')

    assert helpers.get_data(response) == [
        {
            'id': '3',
            'size': 3,
        },
        {
            'id': '4',
            'size': 1,
        },
    ]
    assert helpers.get_meta(response) == {
        'has_next_page': True
    }


def test_page_default(client):
    response = client.get('/page_widgets')

    assert helpers.get_data(response) == [
        {
            'id': '1',
            'size': 1,
        },
        {
            'id': '2',
            'size': 2,
        },
    ]
    assert helpers.get_meta(response) == {
        'has_next_page': True
    }


def test_id_cursor(client):
    response = client.get('/id_cursor_widgets?cursor=WzFd')

    assert helpers.get_data(response) == [
        {
            'id': '2',
            'size': 2,
        },
        {
            'id': '3',
            'size': 3,
        },
    ]
    assert helpers.get_meta(response) == {
        'has_next_page': True,
        'cursors': [
            'WzJd',
            'WzNd',
        ],
    }


def test_id_cursor_default(client):
    response = client.get('/id_cursor_widgets')

    assert helpers.get_data(response) == [
        {
            'id': '1',
            'size': 1,
        },
        {
            'id': '2',
            'size': 2,
        },
    ]
    assert helpers.get_meta(response) == {
        'has_next_page': True,
        'cursors': [
            'WzFd',
            'WzJd',
        ],
    }


def test_id_cursor_sorted(client):
    response = client.get('/id_cursor_widgets?sort=size,-id&cursor=WzEsIDRd')

    assert helpers.get_data(response) == [
        {
            'id': '1',
            'size': 1,
        },
        {
            'id': '5',
            'size': 2,
        },
    ]
    assert helpers.get_meta(response) == {
        'has_next_page': True,
        'cursors': [
            'WzEsIDFd',
            'WzIsIDVd',
        ],
    }


def test_id_cursor_sorted_default(client):
    response = client.get('/id_cursor_widgets?sort=size,-id')

    assert helpers.get_data(response) == [
        {
            'id': '4',
            'size': 1,
        },
        {
            'id': '1',
            'size': 1,
        },
    ]
    assert helpers.get_meta(response) == {
        'has_next_page': True,
        'cursors': [
            'WzEsIDRd',
            'WzEsIDFd',
        ],
    }


# -----------------------------------------------------------------------------


def test_error_invalid_limit_type(client):
    response = client.get('/limit_offset_widgets?limit=foo')
    assert response.status_code == 400

    assert helpers.get_errors(response) == [{
        'code': 'invalid_limit',
        'source': {'parameter': 'limit'},
    }]


def test_error_invalid_limit_value(client):
    response = client.get('/limit_offset_widgets?limit=-1')
    assert response.status_code == 400

    assert helpers.get_errors(response) == [{
        'code': 'invalid_limit',
        'source': {'parameter': 'limit'},
    }]


def test_error_invalid_offset_type(client):
    response = client.get('/limit_offset_widgets?offset=foo')
    assert response.status_code == 400

    assert helpers.get_errors(response) == [{
        'code': 'invalid_offset',
        'source': {'parameter': 'offset'},
    }]


def test_error_invalid_offset_value(client):
    response = client.get('/limit_offset_widgets?offset=-1')
    assert response.status_code == 400

    assert helpers.get_errors(response) == [{
        'code': 'invalid_offset',
        'source': {'parameter': 'offset'},
    }]


def test_error_invalid_page_type(client):
    response = client.get('/page_widgets?page=foo')
    assert response.status_code == 400

    assert helpers.get_errors(response) == [{
        'code': 'invalid_page',
        'source': {'parameter': 'page'},
    }]


def test_error_invalid_page_value(client):
    response = client.get('/page_widgets?page=-1')
    assert response.status_code == 400

    assert helpers.get_errors(response) == [{
        'code': 'invalid_page',
        'source': {'parameter': 'page'},
    }]


def test_error_invalid_cursor_encoding(client):
    response = client.get('/id_cursor_widgets?cursor=foo')
    assert response.status_code == 400

    assert helpers.get_errors(response) == [{
        'code': 'invalid_cursor.encoding',
        'source': {'parameter': 'cursor'},
    }]


def test_error_invalid_cursor_length(client):
    response = client.get('/id_cursor_widgets?cursor=WzEsIDFd')
    assert response.status_code == 400

    assert helpers.get_errors(response) == [{
        'code': 'invalid_cursor.length',
        'source': {'parameter': 'cursor'},
    }]


def test_error_invalid_cursor_field(client):
    response = client.get('/id_cursor_widgets?cursor=WyJmb28iXQ%3D%3D')
    assert response.status_code == 400

    errors = helpers.get_errors(response)
    for error in errors:
        assert error.pop('detail', None) is not None

    assert errors == [{
        'code': 'invalid_cursor',
        'source': {'parameter': 'cursor'},
    }]
