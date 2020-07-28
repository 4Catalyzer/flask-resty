import pytest
from marshmallow import Schema, fields
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import raiseload, relationship

from flask_resty import Api, GenericModelView, Related, RelatedId, RelatedItem
from flask_resty.testing import assert_response

# -----------------------------------------------------------------------------


@pytest.yield_fixture
def models(db):
    class Parent(db.Model):
        __tablename__ = "parents"

        id = Column(Integer, primary_key=True)
        name = Column(String)

    class Child(db.Model):
        __tablename__ = "children"

        id = Column(Integer, primary_key=True)
        name = Column(String)

        parent_id = Column(ForeignKey(Parent.id))
        parent = relationship(
            Parent, foreign_keys=parent_id, backref="children"
        )

        other_parent_id = Column(ForeignKey(Parent.id))
        other_parent = relationship(Parent, foreign_keys=other_parent_id)

    db.create_all()

    yield {"parent": Parent, "child": Child}

    db.drop_all()


@pytest.fixture
def schemas():
    class ParentSchema(Schema):
        id = fields.Integer(as_string=True)
        name = fields.String(required=True)

        children = RelatedItem(
            "ChildSchema", many=True, exclude=("parent", "other_parent")
        )
        child_ids = fields.List(fields.Integer(as_string=True), load_only=True)

    class ChildSchema(Schema):
        @classmethod
        def get_query_options(cls, load):
            return (load.joinedload("parent"), load.joinedload("other_parent"))

        id = fields.Integer(as_string=True)
        name = fields.String(required=True)

        parent = RelatedItem(
            ParentSchema, exclude=("children",), allow_none=True
        )
        parent_id = fields.Integer(
            as_string=True, allow_none=True, load_only=True
        )

        other_parent = fields.Nested(
            ParentSchema, exclude=("children",), allow_none=True
        )

    return {"parent": ParentSchema(), "child": ChildSchema()}


@pytest.fixture(autouse=True)
def routes(app, models, schemas):
    class ParentView(GenericModelView):
        model = models["parent"]
        schema = schemas["parent"]

        related = Related(children=RelatedId(lambda: ChildView(), "child_ids"))

        def get(self, id):
            return self.retrieve(id)

        def put(self, id):
            return self.update(id)

    class NestedParentView(ParentView):
        related = Related(children=lambda: ChildView())

        def put(self, id):
            return self.update(id)

    class ParentWithCreateView(ParentView):
        related = Related(children=Related(models["child"]))

        def put(self, id):
            return self.update(id)

    class ChildView(GenericModelView):
        model = models["child"]
        schema = schemas["child"]

        base_query_options = (raiseload("*"),)

        related = Related(parent=RelatedId(ParentView, "parent_id"))

        def get(self, id):
            return self.retrieve(id)

        def put(self, id):
            return self.update(id)

    class NestedChildView(GenericModelView):
        model = models["child"]
        schema = schemas["child"]

        related = Related(parent=ParentView)

        def put(self, id):
            return self.update(id)

    class ChildWithOtherParentView(ChildView):
        related = ChildView.related | Related(
            other_parent=Related(models["parent"])
        )

    api = Api(app)
    api.add_resource("/parents/<int:id>", ParentView)
    api.add_resource("/nested_parents/<int:id>", NestedParentView)
    api.add_resource("/parents_with_create/<int:id>", ParentWithCreateView)
    api.add_resource("/children/<int:id>", ChildView)
    api.add_resource("/nested_children/<int:id>", NestedChildView)
    api.add_resource(
        "/children_with_other_parent/<int:id>", ChildWithOtherParentView
    )


@pytest.fixture(autouse=True)
def data(db, models):
    db.session.add_all(
        (
            models["parent"](name="Parent"),
            models["child"](name="Child 1"),
            models["child"](name="Child 2"),
        )
    )
    db.session.commit()


# -----------------------------------------------------------------------------


def test_baseline(client):
    parent_response = client.get("/parents/1")
    assert_response(
        parent_response, 200, {"id": "1", "name": "Parent", "children": []}
    )

    child_1_response = client.get("/children/1")
    assert_response(
        child_1_response,
        200,
        {"id": "1", "name": "Child 1", "parent": None, "other_parent": None},
    )

    child_2_response = client.get("/children/2")
    assert_response(
        child_2_response,
        200,
        {"id": "2", "name": "Child 2", "parent": None, "other_parent": None},
    )


def test_single(client):
    response = client.put(
        "/children/1",
        data={"id": "1", "name": "Updated Child", "parent_id": "1"},
    )

    assert_response(
        response,
        200,
        {
            "id": "1",
            "name": "Updated Child",
            "parent": {"id": "1", "name": "Parent"},
            "other_parent": None,
        },
    )


def test_single_nested(client):
    response = client.put(
        "/nested_children/1",
        data={"id": "1", "name": "Updated Child", "parent": {"id": "1"}},
    )

    assert_response(
        response,
        200,
        {
            "id": "1",
            "name": "Updated Child",
            "parent": {"id": "1", "name": "Parent"},
            "other_parent": None,
        },
    )


def test_many(client):
    response = client.put(
        "/parents/1",
        data={"id": "1", "name": "Updated Parent", "child_ids": ["1", "2"]},
    )

    assert_response(
        response,
        200,
        {
            "id": "1",
            "name": "Updated Parent",
            "children": [
                {"id": "1", "name": "Child 1"},
                {"id": "2", "name": "Child 2"},
            ],
        },
    )


def test_many_nested(client):
    response = client.put(
        "/nested_parents/1",
        data={
            "id": "1",
            "name": "Updated Parent",
            "children": [{"id": "1"}, {"id": "2"}],
        },
    )

    assert_response(
        response,
        200,
        {
            "id": "1",
            "name": "Updated Parent",
            "children": [
                {"id": "1", "name": "Child 1"},
                {"id": "2", "name": "Child 2"},
            ],
        },
    )


def test_many_with_create(client):
    response = client.put(
        "/parents_with_create/1",
        data={
            "id": "1",
            "name": "Updated Parent",
            "children": [{"name": "Child 3"}, {"name": "Child 4"}],
        },
    )

    assert_response(
        response,
        200,
        {
            "id": "1",
            "name": "Updated Parent",
            "children": [
                {"id": "3", "name": "Child 3"},
                {"id": "4", "name": "Child 4"},
            ],
        },
    )


def test_missing(client):
    test_single(client)

    response = client.put(
        "/children/1", data={"id": "1", "name": "Twice Updated Child"}
    )

    assert_response(
        response,
        200,
        {
            "id": "1",
            "name": "Twice Updated Child",
            "parent": {"id": "1", "name": "Parent"},
            "other_parent": None,
        },
    )


def test_null(client):
    test_single(client)

    response = client.put(
        "/children/1",
        data={"id": "1", "name": "Twice Updated Child", "parent_id": None},
    )
    assert_response(
        response,
        200,
        {
            "id": "1",
            "name": "Twice Updated Child",
            "parent": None,
            "other_parent": None,
        },
    )


def test_null_nested(client):
    test_single(client)

    response = client.put(
        "/nested_children/1",
        data={"id": "1", "name": "Twice Updated Child", "parent": None},
    )
    assert_response(
        response,
        200,
        {
            "id": "1",
            "name": "Twice Updated Child",
            "parent": None,
            "other_parent": None,
        },
    )


def test_many_falsy(client):
    test_many(client)

    response = client.put(
        "/parents/1",
        data={"id": "1", "name": "Twice Updated Parent", "child_ids": []},
    )

    assert_response(
        response,
        200,
        {"id": "1", "name": "Twice Updated Parent", "children": []},
    )


def test_combine(client):
    response = client.put(
        "/children_with_other_parent/1",
        data={
            "id": "1",
            "name": "Updated Child",
            "parent_id": "1",
            "other_parent": {"id": "2", "name": "Other Parent"},
        },
    )

    assert_response(
        response,
        200,
        {
            "id": "1",
            "name": "Updated Child",
            "parent": {"id": "1", "name": "Parent"},
            "other_parent": {"id": "2", "name": "Other Parent"},
        },
    )


# -----------------------------------------------------------------------------


def test_error_not_found(client):
    response = client.put(
        "/children/1",
        data={"id": "1", "name": "Updated Child", "parent_id": "2"},
    )
    assert_response(
        response,
        422,
        [
            {
                "code": "invalid_related.not_found",
                "source": {"pointer": "/data/parent_id"},
            }
        ],
    )


def test_error_not_found_nested(client):
    response = client.put(
        "/nested_children/1",
        data={"id": "1", "name": "Updated Child", "parent": {"id": "2"}},
    )
    assert_response(
        response,
        422,
        [
            {
                "code": "invalid_related.not_found",
                "source": {"pointer": "/data/parent"},
            }
        ],
    )


def test_error_missing_id(client):
    response = client.put(
        "/nested_children/1",
        data={"id": "1", "name": "Updated Child", "parent": {}},
    )
    assert_response(
        response,
        422,
        [
            {
                "code": "invalid_related.missing_id",
                "source": {"pointer": "/data/parent"},
            }
        ],
    )


def test_error_combine_related_type_error():
    with pytest.raises(TypeError):
        Related() | {}
