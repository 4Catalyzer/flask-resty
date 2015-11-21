from flask import Flask
import flask.ext.sqlalchemy as fsa
import pytest

# -----------------------------------------------------------------------------


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True

    return app


@pytest.fixture
def db(app):
    app.config.update(
        SQLALCHEMY_DATABASE_URI='sqlite://',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    return fsa.SQLAlchemy(app)


@pytest.fixture
def client(app):
    return app.test_client()
