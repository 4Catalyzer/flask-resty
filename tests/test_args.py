import pytest
from marshmallow import Schema, fields

from flask_resty import Api, ApiView
from flask_resty.fields import DelimitedList
from flask_resty.testing import assert_response

# -----------------------------------------------------------------------------


@pytest.fixture
def schemas():
    class NameSchema(Schema):
        name = fields.String(required=True)

    class NameListSchema(Schema):
        names = fields.List(fields.String(), data_key="name", required=True)

    class NameDelimitedListSchema(Schema):
        names = DelimitedList(fields.String(), data_key="name", required=True)

    class NameDefaultSchema(Schema):
        name = fields.String(missing="foo")

    return {
        "name": NameSchema(),
        "name_list": NameListSchema(),
        "name_delimited_list": NameDelimitedListSchema(),
        "name_default": NameDefaultSchema(),
    }


@pytest.fixture
def views(app, schemas):
    class NameView(ApiView):
        args_schema = schemas["name"]

        def get(self):
            return self.make_response(self.request_args["name"])

    class NameListView(ApiView):
        args_schema = schemas["name_list"]

        def get(self):
            return self.make_response(self.request_args["names"])

    class NameDelimitedListView(ApiView):
        args_schema = schemas["name_delimited_list"]

        def get(self):
            return self.make_response(self.request_args["names"])

    class NameDefaultView(ApiView):
        args_schema = schemas["name_default"]

        def get(self):
            return self.make_response(self.request_args["name"])

    return {
        "name": NameView,
        "names": NameListView,
        "names_delimited": NameDelimitedListView,
        "name_default": NameDefaultView,
    }


@pytest.fixture(autouse=True)
def routes(app, views):
    api = Api(app)
    api.add_resource("/name", views["name"])
    api.add_resource("/names", views["names"])
    api.add_resource("/names_delimited", views["names_delimited"])
    api.add_resource("/name_default", views["name_default"])


# -----------------------------------------------------------------------------


def test_get_name_one(client):
    response = client.get("/name?name=foo")
    assert_response(response, 200, "foo")


def test_get_name_extra(client):
    response = client.get("/name?name=foo&ignored=bar")
    assert_response(response, 200, "foo")


def test_get_names_one(client):
    response = client.get("/names?name=foo")
    assert_response(response, 200, ["foo"])


def test_get_names_many(client):
    response = client.get("/names?name=foo&name=bar")
    assert_response(response, 200, ["foo", "bar"])


def test_get_names_many_delimited(client):
    response = client.get("/names_delimited?name=foo,bar")
    assert_response(response, 200, ["foo", "bar"])


def test_get_name_default(client):
    response = client.get("/name_default")
    assert_response(response, 200, "foo")


def test_get_name_default_specified(client):
    response = client.get("/name_default?name=bar")
    assert_response(response, 200, "bar")


def test_caching(app, views):
    with app.test_request_context("/?name=foo"):
        name_view = views["name"]()
        names_view = views["names"]()

        name_view_request_args = name_view.request_args
        names_view_request_args = names_view.request_args

        assert name_view_request_args == {"name": "foo"}
        assert names_view_request_args == {"names": ["foo"]}

        assert name_view.request_args is name_view_request_args
        assert names_view.request_args is names_view_request_args


# -----------------------------------------------------------------------------


def test_error_get_name_missing(client):
    response = client.get("/name")
    assert_response(
        response,
        422,
        [{"code": "invalid_parameter", "source": {"parameter": "name"}}],
    )


def test_error_get_names_missing(client):
    response = client.get("/names")
    assert_response(
        response,
        422,
        [{"code": "invalid_parameter", "source": {"parameter": "name"}}],
    )
