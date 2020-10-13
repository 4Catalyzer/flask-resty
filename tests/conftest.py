import flask_sqlalchemy as fsa
import os
import pytest
from flask import Flask
from flask.testing import FlaskClient

from flask_resty.testing import ApiClient

# -----------------------------------------------------------------------------


@pytest.fixture
def app():
    app = Flask(__name__)
    app.testing = True
    return app


@pytest.fixture
def db(app):
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "sqlite://"
    )

    # TODO: Remove once this is the default.
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    return fsa.SQLAlchemy(app)


@pytest.fixture
def client(app):
    app.test_client_class = ApiClient
    return app.test_client()


@pytest.fixture
def base_client(app):
    app.test_client_class = FlaskClient
    return app.test_client()
