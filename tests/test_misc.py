import pytest
from marshmallow import Schema, fields
from sqlalchemy import Column, Integer

from flask_resty import Api, GenericModelView, StrictRule
from flask_resty.testing import assert_response

# -----------------------------------------------------------------------------


@pytest.yield_fixture
def models(db):
    class Widget(db.Model):
        __tablename__ = "widgets"

        id = Column(Integer, primary_key=True)

    db.create_all()

    yield {"widget": Widget}

    db.drop_all()


@pytest.fixture
def schemas():
    class WidgetSchema(Schema):
        id = fields.Integer(as_string=True)

    return {"widget": WidgetSchema()}


@pytest.fixture
def views(models, schemas):
    class WidgetViewBase(GenericModelView):
        model = models["widget"]
        schema = schemas["widget"]

    class WidgetListView(WidgetViewBase):
        def get(self):
            return self.list()

        def post(self):
            return self.create(allow_client_id=True)

    class WidgetView(WidgetViewBase):
        def get(self, id):
            return self.retrieve(id)

    class CustomWidgetView(WidgetViewBase):
        def delete(self, id):
            return self.destroy(id)

        def update_item_raw(self, widget, data):
            return self.model(id=9)

        def delete_item_raw(self, widget):
            return self.model(id=9)

        def make_deleted_response(self, widget):
            return self.make_item_response(widget)

    return {
        "widget_list": WidgetListView,
        "widget": WidgetView,
        "custom_widget": CustomWidgetView,
    }


@pytest.fixture(autouse=True)
def data(db, models):
    db.session.add(models["widget"]())
    db.session.commit()


# -----------------------------------------------------------------------------


def test_api_prefix(app, views, client, base_client):
    api = Api(app, "/api")
    api.add_resource("/widgets", views["widget_list"])

    response = client.get("/widgets")
    assert_response(response, 200, [{"id": "1"}])

    response = base_client.get("/api/widgets")
    assert_response(response, 200, [{"id": "1"}])


def test_rule_without_slash(app, views, client):
    api = Api(app, "/api")
    api.add_resource("/widgets", views["widget_list"])

    response = client.get("/widgets")
    assert_response(response, 200)

    response = client.get("/widgets/")
    assert_response(response, 404)


def test_rule_with_slash(app, views, client):
    api = Api(app, "/api")
    api.add_resource("/widgets/", views["widget_list"])

    response = client.get("/widgets")
    assert_response(response, 308)

    response = client.get("/widgets/")
    assert_response(response, 200)


def test_no_append_slash(monkeypatch, app, views, client):
    monkeypatch.setattr(app, "url_rule_class", StrictRule)

    api = Api(app, "/api")
    api.add_resource("/widgets/", views["widget_list"])

    response = client.get("/widgets")
    assert_response(response, 404)

    response = client.get("/widgets/")
    assert_response(response, 200)


def test_create_client_id(app, views, client):
    api = Api(app)
    api.add_resource("/widgets", views["widget_list"], views["widget"])

    response = client.post("/widgets", data={"id": "100"})
    assert response.headers["Location"] == "http://localhost/widgets/100"
    assert_response(response, 201, {"id": "100"})


def test_create_no_location(app, views, client):
    views["widget_list"].get_location = lambda self, item: None

    api = Api(app)
    api.add_resource("/widgets", views["widget_list"], views["widget"])

    response = client.post("/widgets", data={})
    assert "Location" not in response.headers
    assert_response(response, 201, {"id": "2"})


def test_training_slash(app, views, client):
    api = Api(app)
    api.add_resource(
        "/widgets/", views["widget_list"], views["widget"], id_rule="<id>/"
    )

    response = client.post("/widgets/", data={"id": "100"})
    assert response.headers["Location"] == "http://localhost/widgets/100/"

    assert_response(response, 201, {"id": "100"})

    response = client.get("/widgets/100/")
    assert response.status_code == 200


def test_resource_rules(app, views, client):
    api = Api(app)
    api.add_resource(
        base_rule="/widget/<id>",
        base_view=views["widget"],
        alternate_rule="/widgets",
        alternate_view=views["widget_list"],
    )

    get_response = client.get("/widget/1")

    assert_response(get_response, 200, {"id": "1"})

    post_response = client.post("/widgets", data={})
    assert post_response.headers["Location"] == "http://localhost/widget/2"

    assert_response(post_response, 201, {"id": "2"})


def test_factory_pattern(app, views, client):
    api = Api()
    api.init_app(app)

    with pytest.raises(AssertionError, match="no application specified"):
        api.add_resource("/widgets", views["widget_list"])

    api.add_resource("/widgets", views["widget_list"], app=app)

    response = client.get("/widgets")
    assert_response(response, 200, [{"id": "1"}])


def test_view_func_wrapper(app, views):
    api = Api(app)
    api.add_resource("/widgets", views["widget_list"], views["widget"])

    # This is really a placeholder for asserting that e.g. custom New Relic
    # view information gets passed through.
    assert app.view_functions["WidgetView"].__name__ == "WidgetView"


def test_delete_return_item(app, views, client):
    api = Api(app)
    api.add_resource("/widgets/<int:id>", views["custom_widget"])

    response = client.delete("/widgets/1")
    assert_response(response, 200, {"id": "9"})
