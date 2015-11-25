from flask.ext.resty import Api, GenericModelView, NestedRelated, RelatedItem
import json
from marshmallow import fields, Schema
import pytest
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

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
        children = RelatedItem(
            'ChildSchema', many=True, required=True, exclude=('parent',),
        )

    class ChildSchema(Schema):
        id = fields.Integer(as_string=True)
        name = fields.String(required=True)
        parent = RelatedItem(
            ParentSchema, required=True, exclude=('children',),
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

        related = NestedRelated(
            children=lambda: ChildView(),
        )

        def get(self, id):
            return self.retrieve(id)

        def put(self, id):
            return self.update(id, return_content=True)

    class ChildView(GenericModelView):
        model = models['child']
        schema = schemas['child']

        related = NestedRelated(
            parent=ParentView,
        )

        def get(self, id):
            return self.retrieve(id)

        def put(self, id):
            return self.update(id, return_content=True)

    api = Api(app, '/api')
    api.add_resource('/parents/<int:id>', ParentView)
    api.add_resource('/children/<int:id>', ChildView)


@pytest.fixture(autouse=True)
def data(db, models):
    def create_item(type, name):
        item = models[type]()
        item.name = name
        return item

    db.session.add_all((
        create_item('parent', "Parent"),
        create_item('child', "Child 1"),
        create_item('child', "Child 2"),
    ))
    db.session.commit()


# -----------------------------------------------------------------------------


def test_baseline(client):
    parent_response = client.get('/api/parents/1')
    assert json.loads(parent_response.data)['data'] == {
        'id': '1',
        'name': "Parent",
        'children': []
    }

    child_1_response = client.get('/api/children/1')
    assert json.loads(child_1_response.data)['data'] == {
        'id': '1',
        'name': "Child 1",
        'parent': None,
    }

    child_2_response = client.get('/api/children/2')
    assert json.loads(child_2_response.data)['data'] == {
        'id': '2',
        'name': "Child 2",
        'parent': None,
    }


def test_single(client):
    response = client.put(
        '/api/children/1',
        content_type='application/json',
        data=json.dumps({
            'data': {
                'id': '1',
                'name': "Updated Child",
                'parent': {'id': '1'},
            },
        }),
    )

    assert json.loads(response.data)['data'] == {
        'id': '1',
        'name': "Updated Child",
        'parent': {
            'id': '1',
            'name': "Parent",
        },
    }


def test_many(client):
    response = client.put(
        '/api/parents/1',
        content_type='application/json',
        data=json.dumps({
            'data': {
                'id': '1',
                'name': "Updated Parent",
                'children': [
                    {'id': '1'},
                    {'id': '2'},
                ],
            },
        }),
    )

    assert json.loads(response.data)['data'] == {
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
