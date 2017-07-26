from flask import Flask
from flask.testing import FlaskClient
import flask_sqlalchemy as fsa
import pytest

from flask_resty.testing import ApiClient

# -----------------------------------------------------------------------------


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True

    return app


@pytest.fixture
def db(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'

    # TODO: Remove once this is the default.
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    return fsa.SQLAlchemy(app)


@pytest.fixture
def client(app):
    app.test_client_class = ApiClient
    return app.test_client()


@pytest.fixture
def base_client(app):
    app.test_client_class = FlaskClient
    return app.test_client()
