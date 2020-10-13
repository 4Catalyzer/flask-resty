import operator
import pytest
from marshmallow import Schema, fields, validate
from sqlalchemy import Column, Integer, String

from flask_resty import (
    Api,
    ColumnFilter,
    Filtering,
    GenericModelView,
    ModelFilter,
    model_filter,
)
from flask_resty.testing import assert_response

# -----------------------------------------------------------------------------


@pytest.yield_fixture
def models(db):
    class Widget(db.Model):
        __tablename__ = "widgets"

        id = Column(Integer, primary_key=True)
        color = Column(String)
        size = Column(Integer)

    db.create_all()

    yield {"widget": Widget}

    db.drop_all()


@pytest.fixture
def schemas():
    class WidgetSchema(Schema):
        id = fields.Integer(as_string=True)
        color = fields.String()
        size = fields.Integer(validate=validate.Range(min=1))

    return {"widget": WidgetSchema()}


@pytest.fixture
def filter_fields():
    @model_filter(fields.String(required=True), separator=None)
    def filter_color_custom(model, value):
        return model.color == value

    return {"color_custom": filter_color_custom}


@pytest.fixture(autouse=True)
def routes(app, models, schemas, filter_fields):
    class WidgetViewBase(GenericModelView):
        model = models["widget"]
        schema = schemas["widget"]

        filtering = Filtering(
            color=operator.eq,
            color_allow_empty=ColumnFilter(
                "color", operator.eq, allow_empty=True
            ),
            size=ColumnFilter(operator.eq, separator="|"),
            size_min=ColumnFilter("size", operator.ge),
            size_divides=ColumnFilter(
                "size", lambda size, value: size % value == 0
            ),
            size_is_odd=ModelFilter(
                fields.Boolean(),
                lambda model, value: model.size % 2 == int(value),
            ),
            size_min_unvalidated=ColumnFilter(
                "size", operator.ge, validate=False
            ),
            size_skip_invalid=ColumnFilter(
                "size", operator.eq, skip_invalid=True
            ),
        )

    class WidgetListView(WidgetViewBase):
        def get(self):
            return self.list()

    class WidgetSizeRequiredListView(WidgetViewBase):
        filtering = WidgetViewBase.filtering | Filtering(
            size=ColumnFilter(operator.eq, required=True)
        )

        def get(self):
            return self.list()

    class WidgetColorCustomListView(WidgetViewBase):
        filtering = Filtering(color=filter_fields["color_custom"])

        def get(self):
            return self.list()

    class WidgetDefaultFiltersView(WidgetViewBase):
        filtering = Filtering(
            color=ModelFilter(
                fields.String(missing="red"),
                lambda model, value: model.color == value,
            ),
            size=ColumnFilter(operator.eq, missing=1),
        )

        def get(self):
            return self.list()

    api = Api(app)
    api.add_resource("/widgets", WidgetListView)
    api.add_resource("/widgets_size_required", WidgetSizeRequiredListView)
    api.add_resource("/widgets_color_custom", WidgetColorCustomListView)
    api.add_resource("/widgets_default_filters", WidgetDefaultFiltersView)


@pytest.fixture(autouse=True)
def data(db, models):
    db.session.add_all(
        (
            models["widget"](color="red", size=1),
            models["widget"](color="green", size=2),
            models["widget"](color="blue", size=3),
            models["widget"](color="red", size=6),
        )
    )
    db.session.commit()


# -----------------------------------------------------------------------------


def test_eq(client):
    response = client.get("/widgets?color=red")
    assert_response(
        response,
        200,
        [
            {"id": "1", "color": "red", "size": 1},
            {"id": "4", "color": "red", "size": 6},
        ],
    )


def test_eq_many(client):
    response = client.get("/widgets?color=green,blue")
    assert_response(
        response,
        200,
        [
            {"id": "2", "color": "green", "size": 2},
            {"id": "3", "color": "blue", "size": 3},
        ],
    )


def test_eq_many_custom_separator(client):
    response = client.get("/widgets?size=2|3")
    assert_response(
        response,
        200,
        [
            {"id": "2", "color": "green", "size": 2},
            {"id": "3", "color": "blue", "size": 3},
        ],
    )


def test_eq_empty_custom_column_element(client):
    response = client.get("/widgets?size=")
    assert_response(response, 200, [])


def test_eq_empty_allow_empty(client):
    response = client.get("/widgets?color_allow_empty=")
    assert_response(response, 200, [])


def test_ge(client):
    response = client.get("/widgets?size_min=3")
    assert_response(
        response,
        200,
        [
            {"id": "3", "color": "blue", "size": 3},
            {"id": "4", "color": "red", "size": 6},
        ],
    )


def test_custom_operator(client):
    response = client.get("/widgets?size_divides=2")
    assert_response(
        response,
        200,
        [
            {"id": "2", "color": "green", "size": 2},
            {"id": "4", "color": "red", "size": 6},
        ],
    )


def test_column_filter_required_present(client):
    response = client.get("/widgets_size_required?size=1")
    assert_response(response, 200, [{"id": "1", "color": "red", "size": 1}])


def test_combine(client):
    response = client.get("/widgets_size_required?size=1&color=green")
    assert_response(response, 200, [])


def test_column_filter_unvalidated(client):
    response = client.get("/widgets?size_min_unvalidated=-1")
    assert_response(
        response, 200, [{"id": "1"}, {"id": "2"}, {"id": "3"}, {"id": "4"}]
    )


def test_column_filter_skip_invalid(client):
    response = client.get("/widgets?size_skip_invalid=foo")
    assert_response(response, 200, [])


def test_model_filter(client):
    response = client.get("/widgets?size_is_odd=true")
    assert_response(
        response,
        200,
        [
            {"id": "1", "color": "red", "size": 1},
            {"id": "3", "color": "blue", "size": 3},
        ],
    )


def test_model_filter_kwargs(client):
    red_response = client.get("/widgets_color_custom?color=red")
    assert_response(
        red_response,
        200,
        [
            {"id": "1", "color": "red", "size": 1},
            {"id": "4", "color": "red", "size": 6},
        ],
    )

    separator_response = client.get("/widgets_color_custom?color=red,blue")
    assert_response(separator_response, 200, [])


def test_model_filter_default(client):
    response = client.get("/widgets_default_filters")
    assert_response(response, 200, [{"id": "1", "color": "red", "size": 1}])


def test_model_filter_default_override(client):
    response = client.get("/widgets_default_filters?color=blue&size=3")
    assert_response(response, 200, [{"id": "3", "color": "blue", "size": 3}])


# -----------------------------------------------------------------------------


def test_error_invalid_type(client):
    response = client.get("/widgets?size_min=foo")
    assert_response(
        response,
        400,
        [
            {
                "code": "invalid_filter",
                "detail": "Not a valid integer.",
                "source": {"parameter": "size_min"},
            }
        ],
    )


def test_error_unvalidated_invalid_type(client):
    response = client.get("/widgets?size_min_unvalidated=foo")
    assert_response(
        response,
        400,
        [
            {
                "code": "invalid_filter",
                "detail": "Not a valid integer.",
                "source": {"parameter": "size_min_unvalidated"},
            }
        ],
    )


def test_error_invalid_value(client):
    response = client.get("/widgets?size_min=-1")
    assert_response(
        response,
        400,
        [{"code": "invalid_filter", "source": {"parameter": "size_min"}}],
    )


def test_error_column_filter_required_missing(client):
    response = client.get("/widgets_size_required")
    assert_response(
        response,
        400,
        [{"code": "invalid_filter.missing", "source": {"parameter": "size"}}],
    )


def test_error_model_filter_required_missing(client):
    response = client.get("/widgets_color_custom")
    assert_response(
        response,
        400,
        [{"code": "invalid_filter.missing", "source": {"parameter": "color"}}],
    )


def test_error_missing_operator():
    ColumnFilter(operator=operator.eq)

    with pytest.raises(TypeError, match="must specify operator"):
        ColumnFilter("size")

    with pytest.raises(TypeError, match="must specify operator"):
        ColumnFilter()


def test_error_reuse_column_filter():
    explicit_column_filter = ColumnFilter("foo", operator.eq)
    implicit_column_filter = ColumnFilter(operator.eq)

    Filtering(foo=explicit_column_filter, bar=explicit_column_filter)

    with pytest.raises(TypeError, match="without explicit column name"):
        Filtering(foo=implicit_column_filter, bar=implicit_column_filter)


def test_error_combine_filtering_type_error():
    with pytest.raises(TypeError):
        Filtering() | {}
