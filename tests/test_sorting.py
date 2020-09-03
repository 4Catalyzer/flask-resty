import pytest
from marshmallow import Schema, fields
from sqlalchemy import Column, Integer, String, sql

from flask_resty import Api, FixedSorting, GenericModelView, Sorting
from flask_resty.testing import assert_response

# -----------------------------------------------------------------------------


@pytest.yield_fixture
def models(db):
    class Widget(db.Model):
        __tablename__ = "widgets"

        id = Column(Integer, primary_key=True)
        name = Column(String)
        content = Column(String)
        size = Column(Integer)

    db.create_all()

    yield {"widget": Widget}

    db.drop_all()


@pytest.fixture
def schemas():
    class WidgetSchema(Schema):
        id = fields.Integer(as_string=True)
        name = fields.String()
        content = fields.String()
        size = fields.Integer()

    return {"widget": WidgetSchema()}


@pytest.fixture(autouse=True)
def routes(app, models, schemas):
    Widget = models["widget"]

    class WidgetListView(GenericModelView):
        model = models["widget"]
        schema = schemas["widget"]

        sorting = Sorting(
            "name",
            "size",
            content_length=sql.func.length(Widget.content),
            content_length2=lambda model, field_name: sql.func.length(
                model.content
            ),
        )

        def get(self):
            return self.list()

    class FixedWidgetListView(WidgetListView):
        sorting = FixedSorting("name,size")

        def get(self):
            return self.list()

    api = Api(app)
    api.add_resource("/widgets", WidgetListView)
    api.add_resource("/fixed_widgets", FixedWidgetListView)


@pytest.fixture(autouse=True)
def data(db, models):
    db.session.add_all(
        (
            models["widget"](name="Foo", size=1, content="Some bold text"),
            models["widget"](name="Foo", size=5, content="Short"),
            models["widget"](
                name="Baz", size=3, content="LorumLorumLorumLorum"
            ),
        )
    )
    db.session.commit()


# -----------------------------------------------------------------------------


def test_single(client):
    response = client.get("/widgets?sort=size")

    assert_response(
        response,
        200,
        [
            {"id": "1", "name": "Foo", "size": 1},
            {"id": "3", "name": "Baz", "size": 3},
            {"id": "2", "name": "Foo", "size": 5},
        ],
    )


def test_many(client):
    response = client.get("/widgets?sort=name,-size")

    assert_response(
        response,
        200,
        [
            {"id": "3", "name": "Baz", "size": 3},
            {"id": "2", "name": "Foo", "size": 5},
            {"id": "1", "name": "Foo", "size": 1},
        ],
    )


def test_no_sort(client):
    response = client.get("/widgets")

    assert_response(
        response,
        200,
        [
            {"id": "1", "name": "Foo", "size": 1},
            {"id": "2", "name": "Foo", "size": 5},
            {"id": "3", "name": "Baz", "size": 3},
        ],
    )


def test_fixed(client):
    response = client.get("/fixed_widgets")

    assert_response(
        response,
        200,
        [
            {"id": "3", "name": "Baz", "size": 3},
            {"id": "1", "name": "Foo", "size": 1},
            {"id": "2", "name": "Foo", "size": 5},
        ],
    )


def test_custom_expression(client):
    response = client.get("/widgets?sort=content_length")

    assert_response(
        response,
        200,
        [
            {"id": "2", "name": "Foo", "content": "Short"},
            {"id": "1", "name": "Foo", "content": "Some bold text"},
            {"id": "3", "name": "Baz", "content": "LorumLorumLorumLorum"},
        ],
    )


def test_custom_callable(client):
    response = client.get("/widgets?sort=content_length2")

    assert_response(
        response,
        200,
        [
            {"id": "2", "name": "Foo", "content": "Short"},
            {"id": "1", "name": "Foo", "content": "Some bold text"},
            {"id": "3", "name": "Baz", "content": "LorumLorumLorumLorum"},
        ],
    )


def test_multiple_named_and_expression_sorts(client):
    response = client.get("/widgets?sort=name,content_length")

    assert_response(
        response,
        200,
        [
            {"id": "3", "name": "Baz", "content": "LorumLorumLorumLorum"},
            {"id": "2", "name": "Foo", "content": "Short"},
            {"id": "1", "name": "Foo", "content": "Some bold text"},
        ],
    )


# -----------------------------------------------------------------------------


def test_error_invalid_field(client):
    response = client.get("/widgets?sort=id")

    assert_response(
        response,
        400,
        [{"code": "invalid_sort", "source": {"parameter": "sort"}}],
    )


def test_error_empty(client):
    response = client.get("/widgets?sort=")
    assert_response(
        response,
        400,
        [{"code": "invalid_sort", "source": {"parameter": "sort"}}],
    )


def test_duplicate_fields(client):
    with pytest.raises(
        ValueError,
        match="Sort field\\(s\\) cannot be passed as both positional and keyword arguments",
    ):
        Sorting("name", "date", date=True)
