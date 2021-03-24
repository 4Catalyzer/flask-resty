import operator
import pytest
from marshmallow import Schema, fields, validate
from sqlalchemy import Column, Integer, Boolean

from flask_resty import (
    Api,
    Filtering,
    GenericModelView,
    LimitOffsetPagination,
    LimitPagination,
    MaxLimitPagination,
    PagePagination,
    RelayCursorPagination,
    Sorting,
)
from flask_resty.testing import assert_response, get_body, get_meta

# -----------------------------------------------------------------------------


def encode_cursor(cursor):
    return RelayCursorPagination(2).encode_cursor(cursor)


@pytest.fixture
def models(db):
    class Widget(db.Model):
        __tablename__ = "widgets"

        id = Column(Integer, primary_key=True)
        size = Column(Integer)
        is_cool = Column(Boolean)

    db.create_all()

    yield {"widget": Widget}

    db.drop_all()


@pytest.fixture
def schemas():
    class WidgetSchema(Schema):
        id = fields.Integer(as_string=True)
        size = fields.Integer()
        is_cool = fields.Boolean()

    class WidgetValidateSchema(WidgetSchema):
        size = fields.Integer(validate=validate.Range(max=1))

    return {
        "widget": WidgetSchema(),
        "widget_validate": WidgetValidateSchema(),
    }


@pytest.fixture(autouse=True)
def routes(app, models, schemas):
    class WidgetListViewBase(GenericModelView):
        model = models["widget"]
        schema = schemas["widget"]

        def get(self):
            return self.list()

        def post(self):
            return self.create()

    class MaxLimitWidgetListView(WidgetListViewBase):
        pagination = MaxLimitPagination(2)

    class OptionalLimitWidgetListView(WidgetListViewBase):
        filtering = Filtering(size=operator.eq)
        pagination = LimitPagination()

    class LimitOffsetWidgetListView(WidgetListViewBase):
        filtering = Filtering(size=operator.eq)
        pagination = LimitOffsetPagination(2, 4)

    class PageWidgetListView(WidgetListViewBase):
        pagination = PagePagination(2)

    class RelayCursorListView(WidgetListViewBase):
        sorting = Sorting("id", "size", "is_cool")
        pagination = RelayCursorPagination(2)

    class RelayCursorNoValidateListView(RelayCursorListView):
        schema = schemas["widget_validate"]

        pagination = RelayCursorPagination(2, validate_values=False)

    api = Api(app)
    api.add_resource("/max_limit_widgets", MaxLimitWidgetListView)
    api.add_resource("/optional_limit_widgets", OptionalLimitWidgetListView)
    api.add_resource("/limit_offset_widgets", LimitOffsetWidgetListView)
    api.add_resource("/page_widgets", PageWidgetListView)
    api.add_resource("/relay_cursor_widgets", RelayCursorListView)
    api.add_resource(
        "/relay_cursor_no_validate_widgets", RelayCursorNoValidateListView
    )


@pytest.fixture(autouse=True)
def data(db, models):
    db.session.add_all(
        (
            models["widget"](id=1, size=1, is_cool=True),
            models["widget"](id=2, size=2, is_cool=False),
            models["widget"](id=3, size=3, is_cool=True),
            models["widget"](id=4, size=1, is_cool=False),
            models["widget"](id=5, size=2, is_cool=False),
            models["widget"](id=6, size=3, is_cool=True),
        )
    )
    db.session.commit()


# -----------------------------------------------------------------------------


def test_max_limit(client):
    response = client.get("/max_limit_widgets")
    assert_response(
        response, 200, [{"id": "1", "size": 1}, {"id": "2", "size": 2}]
    )
    assert get_meta(response) == {"has_next_page": True}


def test_limit(client):
    response = client.get("/optional_limit_widgets?limit=2")
    assert_response(
        response, 200, [{"id": "1", "size": 1}, {"id": "2", "size": 2}]
    )
    assert get_meta(response) == {"has_next_page": True}


def test_unset_limit(client):
    response = client.get("/optional_limit_widgets")
    assert_response(
        response,
        200,
        [
            {"id": "1", "size": 1},
            {"id": "2", "size": 2},
            {"id": "3", "size": 3},
            {"id": "4", "size": 1},
            {"id": "5", "size": 2},
            {"id": "6", "size": 3},
        ],
    )
    assert get_meta(response) == {"has_next_page": False}


def test_limit_offset(client):
    response = client.get("/limit_offset_widgets?offset=2&limit=3")

    assert_response(
        response,
        200,
        [
            {"id": "3", "size": 3},
            {"id": "4", "size": 1},
            {"id": "5", "size": 2},
        ],
    )
    assert get_meta(response) == {"has_next_page": True}


def test_limit_offset_default(client):
    response = client.get("/limit_offset_widgets")

    assert_response(
        response, 200, [{"id": "1", "size": 1}, {"id": "2", "size": 2}]
    )
    assert get_meta(response) == {"has_next_page": True}


def test_limit_offset_limit(client):
    response = client.get("/limit_offset_widgets?limit=3")

    assert_response(
        response,
        200,
        [
            {"id": "1", "size": 1},
            {"id": "2", "size": 2},
            {"id": "3", "size": 3},
        ],
    )
    assert get_meta(response) == {"has_next_page": True}


def test_limit_offset_max_limit(client):
    response = client.get("/limit_offset_widgets?limit=5")

    assert_response(
        response,
        200,
        [
            {"id": "1", "size": 1},
            {"id": "2", "size": 2},
            {"id": "3", "size": 3},
            {"id": "4", "size": 1},
        ],
    )
    assert get_meta(response) == {"has_next_page": True}


def test_limit_offset_offset(client):
    response = client.get("/limit_offset_widgets?offset=2")

    assert_response(
        response, 200, [{"id": "3", "size": 3}, {"id": "4", "size": 1}]
    )
    assert get_meta(response) == {"has_next_page": True}


def test_limit_offset_offset_end(client):
    response = client.get("/limit_offset_widgets?offset=4")

    assert_response(
        response, 200, [{"id": "5", "size": 2}, {"id": "6", "size": 3}]
    )
    assert get_meta(response) == {"has_next_page": False}


def test_limit_offset_offset_truncate(client):
    response = client.get("/limit_offset_widgets?offset=5")

    assert_response(response, 200, [{"id": "6", "size": 3}])
    assert get_meta(response) == {"has_next_page": False}


def test_limit_offset_filtered(client):
    response = client.get("/limit_offset_widgets?size=2&limit=1")

    assert_response(response, 200, [{"id": "2", "size": 2}])
    assert get_meta(response) == {"has_next_page": True}


def test_limit_offset_filtered_offset(client):
    response = client.get("/limit_offset_widgets?size=2&offset=1")

    assert_response(response, 200, [{"id": "5", "size": 2}])
    assert get_meta(response) == {"has_next_page": False}


def test_limit_offset_create(client):
    response = client.post("/limit_offset_widgets", data={"size": 1})

    assert "meta" not in get_body(response)


def test_page(client):
    response = client.get("/page_widgets?page=1")

    assert_response(
        response, 200, [{"id": "3", "size": 3}, {"id": "4", "size": 1}]
    )
    assert get_meta(response) == {"has_next_page": True}


def test_page_default(client):
    response = client.get("/page_widgets")

    assert_response(
        response, 200, [{"id": "1", "size": 1}, {"id": "2", "size": 2}]
    )
    assert get_meta(response) == {"has_next_page": True}


def test_page_create(client):
    response = client.post("/page_widgets", data={"size": 1})

    assert "meta" not in get_body(response)


def test_relay_cursor(client):
    response = client.get("/relay_cursor_widgets?cursor=MQ")

    assert_response(
        response, 200, [{"id": "2", "size": 2}, {"id": "3", "size": 3}]
    )
    assert get_meta(response) == {
        "has_next_page": True,
        "cursors": ["Mg", "Mw"],
    }


def test_relay_cursor_default(client):
    response = client.get("/relay_cursor_widgets")

    assert_response(
        response, 200, [{"id": "1", "size": 1}, {"id": "2", "size": 2}]
    )
    assert get_meta(response) == {
        "has_next_page": True,
        "cursors": ["MQ", "Mg"],
    }


def test_relay_cursor_sorted(client):
    response = client.get("/relay_cursor_widgets?sort=size&cursor=MQ.MQ")

    assert_response(
        response, 200, [{"id": "4", "size": 1}, {"id": "2", "size": 2}]
    )
    assert get_meta(response) == {
        "has_next_page": True,
        "cursors": ["MQ.NA", "Mg.Mg"],
    }


def test_relay_cursor_sorted_default(client):
    response = client.get("/relay_cursor_widgets?sort=size")

    assert_response(
        response, 200, [{"id": "1", "size": 1}, {"id": "4", "size": 1}]
    )
    assert get_meta(response) == {
        "has_next_page": True,
        "cursors": ["MQ.MQ", "MQ.NA"],
    }


def test_relay_cursor_sorted_redundant(client):
    response = client.get("/relay_cursor_widgets?sort=size,id&cursor=MQ.MQ")

    assert_response(
        response, 200, [{"id": "4", "size": 1}, {"id": "2", "size": 2}]
    )
    assert get_meta(response) == {
        "has_next_page": True,
        "cursors": ["MQ.NA", "Mg.Mg"],
    }


def test_relay_cursor_sorted_inverse(client):
    response = client.get("/relay_cursor_widgets?sort=-size&cursor=Mg.NQ")

    assert_response(
        response, 200, [{"id": "2", "size": 2}, {"id": "4", "size": 1}]
    )
    assert get_meta(response) == {
        "has_next_page": True,
        "cursors": ["Mg.Mg", "MQ.NA"],
    }


# Note! Ordering of implicit id follows previous sort order
# (id=6, size=3, is_cool=True)
# (id=3, size=3, is_cool=True)
# (id=1, size=1, is_cool=True)
# (id=5, size=2, is_cool=False)
# (id=4, size=1, is_cool=False)
# (id=2, size=2, is_cool=False)
@pytest.mark.parametrize(
    (
        "sort",
        "cursor",
        "expected",
    ),
    (
        ("is_cool", encode_cursor((False, 5)), [{"id": "1"}, {"id": "3"}]),
        ("is_cool", encode_cursor((False, 2)), [{"id": "4"}, {"id": "5"}]),
        ("is_cool", encode_cursor((True, 1)), [{"id": "3"}, {"id": "6"}]),
        ("is_cool", encode_cursor((True, 3)), [{"id": "6"}]),
        ("is_cool,-id", encode_cursor((False, 2)), [{"id": "6"}, {"id": "3"}]),
        ("-is_cool", encode_cursor((True, 6)), [{"id": "3"}, {"id": "1"}]),
        ("-is_cool", encode_cursor((True, 1)), [{"id": "5"}, {"id": "4"}]),
        ("-is_cool", encode_cursor((False, 5)), [{"id": "4"}, {"id": "2"}]),
        ("-is_cool", encode_cursor((False, 4)), [{"id": "2"}]),
        ("-is_cool,id", encode_cursor((True, 6)), [{"id": "2"}, {"id": "4"}]),
    ),
)
def test_relay_cursor_boolean_sorts(client, sort, cursor, expected):
    response = client.get(f"/relay_cursor_widgets?sort={sort}&cursor={cursor}")

    assert_response(response, 200, expected)


def test_relay_cursor_create(client):
    response = client.post("/relay_cursor_widgets", data={"size": 1})

    assert_response(response, 201, {"size": 1})
    assert get_meta(response) == {"cursor": "Nw"}


def test_relay_cursor_create_sorted(client):
    response = client.post("/relay_cursor_widgets?sort=size", data={"size": 1})

    assert_response(response, 201, {"size": 1})
    assert get_meta(response) == {"cursor": "MQ.Nw"}


def test_relay_cursor_no_validate(app, client):
    response = client.post(
        "/relay_cursor_no_validate_widgets", data={"size": 3}
    )
    assert_response(response, 422)

    response = client.get(
        "/relay_cursor_no_validate_widgets?sort=size&cursor=Mg.Mg"
    )
    assert_response(
        response, 200, [{"id": "5", "size": 2}, {"id": "3", "size": 3}]
    )


# -----------------------------------------------------------------------------


def test_error_invalid_limit_type(client):
    response = client.get("/limit_offset_widgets?limit=foo")
    assert_response(
        response,
        400,
        [{"code": "invalid_limit", "source": {"parameter": "limit"}}],
    )


def test_error_invalid_limit_value(client):
    response = client.get("/limit_offset_widgets?limit=-1")
    assert_response(
        response,
        400,
        [{"code": "invalid_limit", "source": {"parameter": "limit"}}],
    )


def test_error_invalid_offset_type(client):
    response = client.get("/limit_offset_widgets?offset=foo")
    assert_response(
        response,
        400,
        [{"code": "invalid_offset", "source": {"parameter": "offset"}}],
    )


def test_error_invalid_offset_value(client):
    response = client.get("/limit_offset_widgets?offset=-1")
    assert_response(
        response,
        400,
        [{"code": "invalid_offset", "source": {"parameter": "offset"}}],
    )


def test_error_invalid_page_type(client):
    response = client.get("/page_widgets?page=foo")
    assert_response(
        response,
        400,
        [{"code": "invalid_page", "source": {"parameter": "page"}}],
    )


def test_error_invalid_page_value(client):
    response = client.get("/page_widgets?page=-1")
    assert_response(
        response,
        400,
        [{"code": "invalid_page", "source": {"parameter": "page"}}],
    )


def test_error_invalid_relay_cursor_encoding(client):
    response = client.get("/relay_cursor_widgets?cursor=_")
    assert_response(
        response,
        400,
        [
            {
                "code": "invalid_cursor.encoding",
                "source": {"parameter": "cursor"},
            }
        ],
    )


def test_error_invalid_relay_cursor_length(client):
    response = client.get("/relay_cursor_widgets?cursor=MQ.MQ")
    assert_response(
        response,
        400,
        [{"code": "invalid_cursor.length", "source": {"parameter": "cursor"}}],
    )


def test_error_invalid_relay_cursor_field(client):
    response = client.get("/relay_cursor_widgets?cursor=Zm9v")
    assert_response(
        response,
        400,
        [
            {
                "code": "invalid_cursor",
                "detail": "Not a valid integer.",
                "source": {"parameter": "cursor"},
            }
        ],
    )
