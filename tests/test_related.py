from flask_resty import Api, GenericModelView, Related, RelatedItem
from marshmallow import fields, Schema
import pytest
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

import helpers

# -----------------------------------------------------------------------------


@pytest.yield_fixture
def models(db):
    class Parent(db.Model):
        __tablename__ = 'parents'

        id = Column(Integer, primary_key=True)
        name = Column(String)

        children = relationship('Child', backref='parent')

    class Child(db.Model):
        __tablename__ = 'children'

        id = Column(Integer, primary_key=True)
        name = Column(String)

        parent_id = Column(ForeignKey(Parent.id))

    db.create_all()

    yield {
        'parent': Parent,
        'child': Child,
    }

    db.drop_all()


@pytest.fixture
def schemas():
    class ParentSchema(Schema):
        id = fields.Integer(as_string=True)
        name = fields.String(required=True)

        children = RelatedItem('ChildSchema', many=True, exclude=('parent',))

    class ChildSchema(Schema):
        id = fields.Integer(as_string=True)
        name = fields.String(required=True)

        parent = RelatedItem(
            ParentSchema, exclude=('children',), allow_none=True,
        )

    return {
        'parent': ParentSchema(),
        'child': ChildSchema(),
    }


@pytest.fixture(autouse=True)
def routes(app, models, schemas):
    class ParentView(GenericModelView):
        model = models['parent']
        schema = schemas['parent']

        related = Related(
            children=lambda: ChildView(),
        )

        def get(self, id):
            return self.retrieve(id)

        def put(self, id):
            return self.update(id, return_content=True)

    class ChildView(GenericModelView):
        model = models['child']
        schema = schemas['child']

        related = Related(
            parent=ParentView,
        )

        def get(self, id):
            return self.retrieve(id)

        def put(self, id):
            return self.update(id, return_content=True)

    api = Api(app)
    api.add_resource('/parents/<int:id>', ParentView)
    api.add_resource('/children/<int:id>', ChildView)


@pytest.fixture(autouse=True)
def data(db, models):
    db.session.add_all((
        models['parent'](name="Parent"),
        models['child'](name="Child 1"),
        models['child'](name="Child 2"),
    ))
    db.session.commit()


# -----------------------------------------------------------------------------


def test_baseline(client):
    parent_response = client.get('/parents/1')
    assert helpers.get_data(parent_response) == {
        'id': '1',
        'name': "Parent",
        'children': [],
    }

    child_1_response = client.get('/children/1')
    assert helpers.get_data(child_1_response) == {
        'id': '1',
        'name': "Child 1",
        'parent': None,
    }

    child_2_response = client.get('/children/2')
    assert helpers.get_data(child_2_response) == {
        'id': '2',
        'name': "Child 2",
        'parent': None,
    }


def test_single(client):
    response = helpers.request(
        client,
        'PUT', '/children/1',
        {
            'id': '1',
            'name': "Updated Child",
            'parent': {'id': '1'},
        },
    )

    assert helpers.get_data(response) == {
        'id': '1',
        'name': "Updated Child",
        'parent': {
            'id': '1',
            'name': "Parent",
        },
    }


def test_many(client):
    response = helpers.request(
        client,
        'PUT', '/parents/1',
        {
            'id': '1',
            'name': "Updated Parent",
            'children': [
                {'id': '1'},
                {'id': '2'},
            ],
        },
    )

    assert helpers.get_data(response) == {
        'id': '1',
        'name': "Updated Parent",
        'children': [
            {
                'id': '1',
                'name': "Child 1",
            },
            {
                'id': '2',
                'name': "Child 2",
            },
        ],
    }


def test_missing(client):
    test_single(client)

    response = helpers.request(
        client,
        'PUT', '/children/1',
        {
            'id': '1',
            'name': "Twice Updated Child",
        },
    )

    assert helpers.get_data(response) == {
        'id': '1',
        'name': "Twice Updated Child",
        'parent': {
            'id': '1',
            'name': "Parent",
        },
    }


def test_null(client):
    test_single(client)

    response = helpers.request(
        client,
        'PUT', '/children/1',
        {
            'id': '1',
            'name': "Twice Updated Child",
            'parent': None,
        },
    )

    assert helpers.get_data(response) == {
        'id': '1',
        'name': "Twice Updated Child",
        'parent': None,
    }


def test_many_falsy(client):
    test_many(client)

    response = helpers.request(
        client,
        'PUT', '/parents/1',
        {
            'id': '1',
            'name': "Twice Updated Parent",
            'children': [],
        },
    )

    assert helpers.get_data(response) == {
        'id': '1',
        'name': "Twice Updated Parent",
        'children': [],
    }


# -----------------------------------------------------------------------------


def test_error_not_found(client):
    response = helpers.request(
        client,
        'PUT', '/children/1',
        {
            'id': '1',
            'name': "Updated Child",
            'parent': {'id': '2'},
        },
    )
    assert response.status_code == 422

    assert helpers.get_errors(response) == [{
        'code': 'invalid_related.not_found',
        'source': {'pointer': '/data/parent'},
    }]


def test_error_missing_id(client):
    response = helpers.request(
        client,
        'PUT', '/children/1',
        {
            'id': '1',
            'name': "Updated Child",
            'parent': {},
        },
    )
    assert response.status_code == 422

    assert helpers.get_errors(response) == [{
        'code': 'invalid_related.missing_id',
        'source': {'pointer': '/data/parent'},
    }]
