import json

from marshmallow import fields, Schema
import pytest
from sqlalchemy import Column, Integer, String

from flask_resty import Api, GenericModelView, HasAnyCredentialsAuthorization
from flask_resty.testing import assert_response

# -----------------------------------------------------------------------------

try:
    from flask_resty import JwkSetAuthentication
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
    with open('tests/keys/testkey_rsa.json', 'r') as rsa_pub_file:
        app.config.update({
            'RESTY_JWT_DECODE_KEY_SET': json.load(rsa_pub_file),
            'RESTY_JWT_DECODE_ALGORITHMS': ['RS256'],
        })

    authentication = JwkSetAuthentication(issuer='resty')

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
    db.session.add_all((
        models['widget'](owner_id='foo'),
        models['widget'](owner_id='bar'),
    ))
    db.session.commit()


@pytest.fixture
def token():
    return 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImZvby5jb20ifQ.eyJpc3MiOiJyZXN0eSIsInN1YiI6ImZvbyJ9.MtJh53tADtv9a-7TrawSP-sV1Q18ouvMi_846XVR_UpM9ZjmAA_QNDModLYCe_Sp3iUWKldG9mk9xbXCf3YIiFGWHHDFCn33z-UqQRrX3IX3awUhVGIyiohO5xB_vxWj36R-HoCvewceJjiBEiYVEA9oxkObEKl-KRAaNA7zM65wzL39fcPk8pFmH_vZN2X4eTzyFrigTLYHHxDLho-huUIWYMxjdVEY79FfA1Ba6rh1RkyaOjeXI4y7MyHPZVaeb_Oh3hsMbyDRgLD5pYeAHB_gGUDwbYmmYxC2k-OfHk52OfmdUyAlxtCfasfhxgvQIrAI0DHKT8Cw7BIt0QKJaA'  # noqa: E501


@pytest.fixture(
    params=(
        'foo',
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJyZXN0eSIsInN1YiI6ImZvbyJ9.qke42KAZLaqSJiTWntnxlcLpmlsWjx6G9lkrAlLSeGM',  # noqa: E501
        'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImZvby5jb20ifQ.eyJpc3MiOiJyZXN0eV8iLCJzdWIiOiJmb28ifQ.nYHHNJ-qB9JYq-2gvPYbcbeZDirm9Iotl8LnUOWU9-SamklURXBGnr3UnHmzUWsB25FBUBGN-4vTO60yEvmUX4iU2RqojPbcylfZx2MNDtyEpyJ5Wxj6bAhHDxv5uqhgZU4Qfh111m9LJzOSj1Tm2In98vmWpj6ZY4GU_FoK65NXBeNynPh42azTD0rXX5rRyQrq2w367AgeZMfoIrHBECS_IA5pmiRuuNe_SwYNFHihw5KVPe1nJ7YaZBj3kMiht24yJwOdxeId5z-t5omU2dA35hACAm14EgHiARfhdXquQ-fE1WD3EzoMBS99Kf-K7533TI47TJEu2Jwu9JOpsg',  # noqa: E501
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

    assert_response(response, 200, [
        {
            'id': '1',
            'owner_id': 'foo',
        },
    ])


def test_arg(client, token):
    response = client.get('/widgets?id_token={}'.format(token))
    assert_response(response, 200, [
        {
            'id': '1',
            'owner_id': 'foo',
        },
    ])


# -----------------------------------------------------------------------------


def test_error_unauthenticated(client):
    response = client.get('/widgets')
    assert_response(response, 401, [{
        'code': 'invalid_credentials.missing',
    }])


def test_error_invalid_authorization(client):
    response = client.get(
        '/widgets',
        headers={
            'Authorization': 'foo',
        },
    )
    assert_response(response, 401, [{
        'code': 'invalid_authorization',
    }])


def test_error_invalid_authorization_scheme(client):
    response = client.get(
        '/widgets',
        headers={
            'Authorization': 'foo bar',
        },
    )
    assert_response(response, 401, [{
        'code': 'invalid_authorization.scheme',
    }])


def test_error_invalid_token(client, invalid_token):
    response = client.get(
        '/widgets',
        headers={
            'Authorization': 'Bearer {}'.format(invalid_token),
        },
    )
    assert_response(response, 401, [{
        'code': 'invalid_token',
    }])
