import pytest
from unittest.mock import ANY

from flask_resty.testing import ApiClient, assert_response, assert_shape

from . import app


@pytest.fixture(scope="session")
def db():
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    database = app.extensions["sqlalchemy"].db
    database.create_all()
    return database


@pytest.fixture(autouse=True)
def clean_tables(db):
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())

    db.session.commit()
    yield
    db.session.rollback()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app, "testing", True)
    monkeypatch.setattr(app, "test_client_class", ApiClient)
    return app.test_client()


def test_create_and_retrieve_author(client):
    response = client.post("/authors/", data={"name": "Fred Brooks"})
    data = assert_response(response, 201)
    assert_shape(data, {"id": ANY, "name": "Fred Brooks", "created_at": ANY})
    # Could also write:
    # assert_response(response, 201, {"id": ANY, "name": "Fred Brooks", "created_at": ANY})
    response = client.get("/authors/")
    assert_response(response, 200, [{"name": "Fred Brooks"}])


def test_create_and_retrieve_book(client):
    response = client.post("/authors/", data={"name": "Fred Brooks"})
    data = assert_response(response, 201)
    author_id = data["id"]

    response = client.post(
        "/books/",
        data={
            "title": "The Mythical Man-Month",
            "author_id": author_id,
            "published_at": "1995-08-12T00:00:00+00:00",
        },
    )
    assert_response(
        response,
        201,
        {
            "id": ANY,
            "title": "The Mythical Man-Month",
            "published_at": "1995-08-12T00:00:00",
            "created_at": ANY,
        },
    )

    response = client.get(f"/books/?author_id={author_id}")
    assert_response(response, 200, [{"title": "The Mythical Man-Month"}])
