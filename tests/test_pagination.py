import operator

import pytest
from marshmallow import Schema, fields, validate
from sqlalchemy import Boolean, Column, Integer, Text

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
        name = Column(Text)

    db.create_all()

    yield {"widget": Widget}

    db.drop_all()


@pytest.fixture
def schemas():
    class WidgetSchema(Schema):
        id = fields.Integer(as_string=True)
        size = fields.Integer()
        name = fields.String()
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


@pytest.fixture()
def add_widgets(db, models):
    def impl(widgets):
        db.session.add_all([models["widget"](**data) for data in widgets])
        db.session.commit()

    return impl


@pytest.fixture()
def data(db, models):
    db.session.add_all(
        (
            models["widget"](id=1, size=1, is_cool=True, name="Whatzit"),
            models["widget"](id=2, size=2, is_cool=False, name="AAA Time"),
            models["widget"](id=3, size=3, is_cool=True, name="Plus Ultra"),
            models["widget"](id=4, size=1, is_cool=False, name="Zendaz"),
            models["widget"](id=5, size=2, is_cool=False, name="Fooz"),
            models["widget"](id=6, size=3, is_cool=True, name="Doodad"),
        )
    )
    db.session.commit()


# -----------------------------------------------------------------------------


def test_max_limit(client, data):
    response = client.get("/max_limit_widgets")
    assert_response(
        response, 200, [{"id": "1", "size": 1}, {"id": "2", "size": 2}]
    )
    assert get_meta(response) == {"has_next_page": True}


def test_limit(client, data):
    response = client.get("/optional_limit_widgets?limit=2")
    assert_response(
        response, 200, [{"id": "1", "size": 1}, {"id": "2", "size": 2}]
    )
    assert get_meta(response) == {"has_next_page": True}


def test_unset_limit(client, data):
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


def test_limit_offset(client, data):
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


def test_limit_offset_default(client, data):
    response = client.get("/limit_offset_widgets")

    assert_response(
        response, 200, [{"id": "1", "size": 1}, {"id": "2", "size": 2}]
    )
    assert get_meta(response) == {"has_next_page": True}


def test_limit_offset_limit(client, data):
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


def test_limit_offset_max_limit(client, data):
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


def test_limit_offset_offset(client, data):
    response = client.get("/limit_offset_widgets?offset=2")

    assert_response(
        response, 200, [{"id": "3", "size": 3}, {"id": "4", "size": 1}]
    )
    assert get_meta(response) == {"has_next_page": True}


def test_limit_offset_offset_end(client, data):
    response = client.get("/limit_offset_widgets?offset=4")

    assert_response(
        response, 200, [{"id": "5", "size": 2}, {"id": "6", "size": 3}]
    )
    assert get_meta(response) == {"has_next_page": False}


def test_limit_offset_offset_truncate(client, data):
    response = client.get("/limit_offset_widgets?offset=5")

    assert_response(response, 200, [{"id": "6", "size": 3}])
    assert get_meta(response) == {"has_next_page": False}


def test_limit_offset_filtered(client, data):
    response = client.get("/limit_offset_widgets?size=2&limit=1")

    assert_response(response, 200, [{"id": "2", "size": 2}])
    assert get_meta(response) == {"has_next_page": True}


def test_limit_offset_filtered_offset(client, data):
    response = client.get("/limit_offset_widgets?size=2&offset=1")

    assert_response(response, 200, [{"id": "5", "size": 2}])
    assert get_meta(response) == {"has_next_page": False}


def test_limit_offset_create(client, data):
    response = client.post("/limit_offset_widgets", data={"size": 1})

    assert "meta" not in get_body(response)


def test_page(client, data):
    response = client.get("/page_widgets?page=1")

    assert_response(
        response, 200, [{"id": "3", "size": 3}, {"id": "4", "size": 1}]
    )
    assert get_meta(response) == {"has_next_page": True}


def test_page_default(client, data):
    response = client.get("/page_widgets")

    assert_response(
        response, 200, [{"id": "1", "size": 1}, {"id": "2", "size": 2}]
    )
    assert get_meta(response) == {"has_next_page": True}


def test_page_create(client, data):
    response = client.post("/page_widgets", data={"size": 1})

    assert "meta" not in get_body(response)


def test_relay_cursor(client, data):
    response = client.get("/relay_cursor_widgets?cursor=MQ")

    assert_response(
        response, 200, [{"id": "2", "size": 2}, {"id": "3", "size": 3}]
    )
    assert get_meta(response) == {
        "has_next_page": True,
        "cursors": ["Mg", "Mw"],
    }


def test_relay_cursor_default(client, data):
    response = client.get("/relay_cursor_widgets")

    assert_response(
        response, 200, [{"id": "1", "size": 1}, {"id": "2", "size": 2}]
    )
    assert get_meta(response) == {
        "has_next_page": True,
        "cursors": ["MQ", "Mg"],
    }


def test_relay_cursor_sorted(client, data):
    response = client.get("/relay_cursor_widgets?sort=size&cursor=MQ.MQ")

    assert_response(
        response, 200, [{"id": "4", "size": 1}, {"id": "2", "size": 2}]
    )
    assert get_meta(response) == {
        "has_next_page": True,
        "cursors": ["MQ.NA", "Mg.Mg"],
    }


def test_relay_cursor_sorted_default(client, data):
    response = client.get("/relay_cursor_widgets?sort=size")

    assert_response(
        response, 200, [{"id": "1", "size": 1}, {"id": "4", "size": 1}]
    )
    assert get_meta(response) == {
        "has_next_page": True,
        "cursors": ["MQ.MQ", "MQ.NA"],
    }


def test_relay_cursor_sorted_redundant(client, data):
    response = client.get("/relay_cursor_widgets?sort=size,id&cursor=MQ.MQ")

    assert_response(
        response, 200, [{"id": "4", "size": 1}, {"id": "2", "size": 2}]
    )
    assert get_meta(response) == {
        "has_next_page": True,
        "cursors": ["MQ.NA", "Mg.Mg"],
    }


def test_relay_cursor_sorted_inverse(client, data):
    response = client.get("/relay_cursor_widgets?sort=-size&cursor=Mg.NQ")

    assert_response(
        response, 200, [{"id": "2", "size": 2}, {"id": "4", "size": 1}]
    )
    assert get_meta(response) == {
        "has_next_page": True,
        "cursors": ["Mg.Mg", "MQ.NA"],
    }


def test_relay_reverse_cursor(client, add_widgets):
    add_widgets(
        (
            {"id": "1", "size": 2},
            {"id": "2", "size": 2},
            {"id": "3", "size": 1},
            {"id": "4", "size": 5},
            {"id": "5", "size": 3},
        )
    )

    first_three_items = [
        {"id": "3", "size": 1},
        {"id": "1", "size": 2},
        {"id": "2", "size": 2},
    ]

    resp = client.get("/relay_cursor_widgets?sort=size&limit=3")
    assert_response(resp, 200, first_three_items)

    # this should be the next item in the list above
    before = encode_cursor((3, "5"))
    resp = client.get(
        f"/relay_cursor_widgets?sort=size&limit=3&before={before}"
    )
    assert_response(resp, 200, first_three_items)

    resp = client.get(f"/relay_cursor_widgets?sort=size&before={before}")

    assert_response(resp, 200, first_three_items[1:])

    assert get_meta(resp) == {
        "has_next_page": True,
        "cursors": [encode_cursor((2, "1")), encode_cursor((2, "2"))],
    }


def test_relay_reverse_cursor_inverse(client, add_widgets):
    add_widgets(
        (
            {"id": "1", "size": 2},
            {"id": "2", "size": 2},
            {"id": "3", "size": 1},
            {"id": "4", "size": 5},
            {"id": "5", "size": 3},
        )
    )

    first_three_items = [
        {"id": "4", "size": 5},
        {"id": "5", "size": 3},
        {"id": "2", "size": 2},
    ]

    resp = client.get("/relay_cursor_widgets?sort=-size&limit=3")
    assert_response(resp, 200, first_three_items)

    # this should be the next item in the list above
    before = encode_cursor((2, "1"))
    resp = client.get(
        f"/relay_cursor_widgets?sort=-size&limit=3&before={before}"
    )
    assert_response(resp, 200, first_three_items)

    resp = client.get(f"/relay_cursor_widgets?sort=-size&before={before}")

    assert_response(resp, 200, first_three_items[1:])

    assert get_meta(resp) == {
        "has_next_page": True,
        "cursors": [encode_cursor((3, "5")), encode_cursor((2, "2"))],
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
def test_relay_cursor_boolean_sorts(client, sort, cursor, expected, data):
    response = client.get(f"/relay_cursor_widgets?sort={sort}&cursor={cursor}")

    assert_response(response, 200, expected)


def test_relay_cursor_create(client, data):
    response = client.post("/relay_cursor_widgets", data={"size": 1})

    assert_response(response, 201, {"size": 1})
    assert get_meta(response) == {"cursor": "Nw"}


def test_relay_cursor_create_sorted(client, data):
    response = client.post("/relay_cursor_widgets?sort=size", data={"size": 1})

    assert_response(response, 201, {"size": 1})
    assert get_meta(response) == {"cursor": "MQ.Nw"}


def test_relay_cursor_no_validate(app, client, data):
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


def test_error_invalid_limit_type(client, data):
    response = client.get("/limit_offset_widgets?limit=foo")
    assert_response(
        response,
        400,
        [{"code": "invalid_limit", "source": {"parameter": "limit"}}],
    )


def test_error_invalid_limit_value(client, data):
    response = client.get("/limit_offset_widgets?limit=-1")
    assert_response(
        response,
        400,
        [{"code": "invalid_limit", "source": {"parameter": "limit"}}],
    )


def test_error_invalid_offset_type(client, data):
    response = client.get("/limit_offset_widgets?offset=foo")
    assert_response(
        response,
        400,
        [{"code": "invalid_offset", "source": {"parameter": "offset"}}],
    )


def test_error_invalid_offset_value(client, data):
    response = client.get("/limit_offset_widgets?offset=-1")
    assert_response(
        response,
        400,
        [{"code": "invalid_offset", "source": {"parameter": "offset"}}],
    )


def test_error_invalid_page_type(client, data):
    response = client.get("/page_widgets?page=foo")
    assert_response(
        response,
        400,
        [{"code": "invalid_page", "source": {"parameter": "page"}}],
    )


def test_error_invalid_page_value(client, data):
    response = client.get("/page_widgets?page=-1")
    assert_response(
        response,
        400,
        [{"code": "invalid_page", "source": {"parameter": "page"}}],
    )


def test_error_invalid_relay_cursor_encoding(client, data):
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


def test_error_invalid_relay_cursor_length(client, data):
    response = client.get("/relay_cursor_widgets?cursor=MQ.MQ")
    assert_response(
        response,
        400,
        [{"code": "invalid_cursor.length", "source": {"parameter": "cursor"}}],
    )


def test_error_invalid_relay_cursor_field(client, data):
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
