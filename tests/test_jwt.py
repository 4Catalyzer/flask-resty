from flask_resty import Api, GenericModelView, HasAnyCredentialsAuthorization
from marshmallow import fields, Schema
import pytest
from sqlalchemy import Column, Integer, String

import helpers

# -----------------------------------------------------------------------------

try:
    from flask_resty import JwtAuthentication
except ImportError:
    pytestmark = pytest.mark.skipif(True, reason="JWT support not installed")

# -----------------------------------------------------------------------------


@pytest.yield_fixture
def models(db):
    class Widget(db.Model):
        __tablename__ = 'widgets'

        id = Column(Integer, primary_key=True)
        owner_id = Column(String)

    db.create_all()

    yield {
        'widget': Widget,
    }

    db.drop_all()


@pytest.fixture
def schemas():
    class WidgetSchema(Schema):
        id = fields.Integer(as_string=True)
        owner_id = fields.String()

    return {
        'widget': WidgetSchema(),
    }


@pytest.fixture
def auth(app):
    app.config.update({
        'RESTY_JWT_DECODE_KEY': 'secret',
        'RESTY_JWT_DECODE_ALGORITHMS': ['HS256'],
    })
    authentication = JwtAuthentication(issuer='resty')

    class UserAuthorization(HasAnyCredentialsAuthorization):
        def filter_query(self, query, view):
            return query.filter(
                view.model.owner_id == self.get_request_credentials()['sub'],
            )

    return {
        'authentication': authentication,
        'authorization': UserAuthorization(),
    }


@pytest.fixture(autouse=True)
def routes(app, models, schemas, auth):
    class WidgetListView(GenericModelView):
        model = models['widget']
        schema = schemas['widget']

        authentication = auth['authentication']
        authorization = auth['authorization']

        def get(self):
            return self.list()

    api = Api(app)
    api.add_resource('/widgets', WidgetListView)


@pytest.fixture(autouse=True)
def data(db, models):
    def create_widget(owner_id):
        widget = models['widget']()
        widget.owner_id = owner_id
        return widget

    db.session.add_all((
        create_widget('foo'),
        create_widget('bar'),
    ))
    db.session.commit()


@pytest.fixture
def token():
    return 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJyZXN0eSIsInN1YiI6ImZvbyJ9.VTeYS-G0nJzYoWatqbHHNt0bFKPBuEoz0TFbPQEwTak'  # noqa


@pytest.fixture(
    params=(
        'foo',
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJyZXN0eSIsInN1YiI6ImZvbyJ9.qke42KAZLaqSJiTWntnxlcLpmlsWjx6G9lkrAlLSeGM',  # noqa
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJyZXN0eV8iLCJzdWIiOiJmb28ifQ.Y4upHw_3ZnQxm7eLb1Uda7jlIMNFQNsWWC80Vocj2MI',  # noqa
    ),
    ids=(
        'malformed',
        'key_mismatch',
        'iss_mismatch',
    ),
)
def invalid_token(request):
    return request.param


# -----------------------------------------------------------------------------


def test_header(client, token):
    response = client.get(
        '/widgets',
        headers={
            'Authorization': 'Bearer {}'.format(token),
        },
    )

    assert helpers.get_data(response) == [
        {
            'id': '1',
            'owner_id': 'foo',
        },
    ]


def test_arg(client, token):
    response = client.get('/widgets?id_token={}'.format(token))

    assert helpers.get_data(response) == [
        {
            'id': '1',
            'owner_id': 'foo',
        },
    ]


# -----------------------------------------------------------------------------


def test_error_unauthenticated(client):
    response = client.get('/widgets')
    assert response.status_code == 401

    assert helpers.get_errors(response) == [{
        'code': 'invalid_credentials.missing',
    }]


def test_error_invalid_authorization(client):
    response = client.get(
        '/widgets',
        headers={
            'Authorization': 'foo',
        },
    )
    assert response.status_code == 401

    assert helpers.get_errors(response) == [{
        'code': 'invalid_authorization',
    }]


def test_error_invalid_authorization_scheme(client):
    response = client.get(
        '/widgets',
        headers={
            'Authorization': 'foo bar',
        },
    )
    assert response.status_code == 401

    assert helpers.get_errors(response) == [{
        'code': 'invalid_authorization.scheme',
    }]


def test_error_invalid_token(client, invalid_token):
    response = client.get(
        '/widgets',
        headers={
            'Authorization': 'Bearer {}'.format(invalid_token),
        },
    )
    assert response.status_code == 401

    assert helpers.get_errors(response) == [{
        'code': 'invalid_token',
    }]
