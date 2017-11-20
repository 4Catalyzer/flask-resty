from marshmallow import fields, Schema
import pytest
from sqlalchemy import Column, Integer, String

from flask_resty import Api, GenericModelView, HasAnyCredentialsAuthorization
from flask_resty.testing import assert_response

# -----------------------------------------------------------------------------

try:
    from flask_resty import JwtAuthentication
    from jwt.utils import force_bytes
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.serialization import (
        load_ssh_public_key,
    )
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
    with open('tests/keys/testkey_rsa.pub', 'r') as rsa_pub_file:
        app.config.update({
            'RESTY_JWT_DECODE_KEY': {
                'foo.com': load_ssh_public_key(
                    force_bytes(rsa_pub_file.read()),
                    backend=default_backend(),
                ),
            },
            'RESTY_JWT_DECODE_ALGORITHMS': ['RS256'],
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
    db.session.add_all((
        models['widget'](owner_id='foo'),
        models['widget'](owner_id='bar'),
    ))
    db.session.commit()


@pytest.fixture
def token():
    return 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImZvby5jb20ifQ.eyJpc3MiOiJyZXN0eSIsInN1YiI6ImZvbyJ9.BTInJ8AoZlVWchR9BOSvad2rpIpDppmXicfliljuvx_x0753qz76m7sY6DjsNJgg6cUKxDpC6DONqmsesofOdxr9zyj-3Doud4TD1vxxnvQ603M0j-OklOr9omIpzwzdrRPwY38FPqruS4mh4WxslWbiU_8sInxwHVVuGGsTQ8jn2SBEk3UiV0YC0t7u7BwdjNIttZcOyIw2zHf9tU7CUPwwFu000DQslqpM5fD5jjkVuGp_NFU7S-otrPND52YV0GZHMXbOpeLMNkQbjm_iybU25VSiooq3eChDP5meCI3fhtm0yDFsJY5SNaV2x3pzPxt4hUrVI93DRj7AhJSjtQ'  # noqa: E501


@pytest.fixture(
    params=(
        'foo',
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJyZXN0eSIsInN1YiI6ImZvbyJ9.qke42KAZLaqSJiTWntnxlcLpmlsWjx6G9lkrAlLSeGM',  # noqa: E501
        'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImZvby5jb20ifQ.eyJpc3MiOiJyZXN0eV8iLCJzdWIiOiJmb28ifQ.QvrwQ_Nrccg7UgiQ7guK8sWKNBTA0vMdB1rxHNqwtSmADzt1xfUcXPyzkG1MQ5-QEwua9bkSV2rFURE4yBIFnSCwdjoPj4vgNNEWs3CtqT3VVaWScfXiCBjs1DjJ3D0eY_6SYnBKiAoSeagQxD6JkNsEdG5GeR3aCvgTyBWYYEEq5sn9n-xyjo6fZNQHV1lbKQnRhUSnz074axOFTZIcMulLC3L3tQT08X3AfyjzsgFDp67AXXtob-aCyEznIhuDhYyea5mGGRWCbKmCTTqTU7xqc9aKm49983pupAw-Xz5eywbIxVVM6gNC_D93DJcwemnw7RCA-qaSZlWxFPe5uw',  # noqa: E501
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
