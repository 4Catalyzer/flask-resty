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


@pytest.fixture(
    params=[
        'tests/keys/testkey_rsa_pub.json',
        'tests/keys/testkey_rsa_cert.json',
    ],
    ids=['public key', 'cert'],
)
def jwk_set(request):
    with open(request.param, 'r') as rsa_pub_file:
        return json.load(rsa_pub_file)


@pytest.fixture()
def auth(app, jwk_set):
    app.config.update({
        'RESTY_JWT_DECODE_JWK_SET': jwk_set,
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
    return 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImZvby5jb20ifQ.eyJpc3MiOiJyZXN0eSIsInN1YiI6ImZvbyJ9.0hkDQT1lnMoGjweZeJDeSfVMllhzlmYtSqErpeU5pp7TK5OkIoLeMCSHjqYdCOwwha8znK6hBxKO-LzT4PPuhe0LnNb_qZpEbtoX6ldN8LSkhCv3Jr8lwt_hs09-lHXxdrknuYmooICI6Q66QzOpTSF4j867UwUYtfVsMpfofxpiRCJOOvynpquYGbgXc59SGJjM5wPAgYo782uRErnRFX7YJmwt5wINjvsKhr0Ry512w_EC--jDGEpcWaNKMDXKL0UMQXWoOM5IlUMA7Kr2bF966X2xuUdRnJinVGnJvdK8yKyZg_qPA26OygLeJUqF-R4jVC-lYEfte7EOLpYBBQ'  # noqa: E501


@pytest.fixture(
    params=(
        'foo',
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJyZXN0eSIsInN1YiI6ImZvbyJ9.qke42KAZLaqSJiTWntnxlcLpmlsWjx6G9lkrAlLSeGM',  # noqa: E501
        'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImZvby5jb20ifQ.eyJpc3MiOiJyZXN0eV8iLCJzdWIiOiJmb28ifQ.zow1JvW0ExAT7hNld7CIi7xox372OcX2ZQn1MdZJVeCTPvwgJi9MkFZ76xJbl_b3_4PW40Hh5TwE8X5U_eTiv7mGeQkc7jOi4wnynHoBHkIO6vqNdrUdob93iePxkxn_xrUvQiR7ROfpQa7IREQ_i8infFKURl4xZR11A0OR6RTboXckfsq1uuOet0TuFCeuBUGbbDy6YNYxBou82qbFLYsFynaUhKBcbLGETM05X_NxTs1fsEXesKrtgdbiM-Lj0N9AeSd7dEH9O0zXcix8kEN4txmxmXrbzSTpWw2PhlMQULPAXpFKk2uiWBdpHlG2nPb2XKsAAXXuN4ZXQ0X1Sw',  # noqa: E501
        'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Im5vcGUifQ.eyJpc3MiOiJyZXN0eSIsInN1YiI6ImZvbyJ9.dUHYJ0SVum7ZY1z7CVivLWpCIPms2FS9dukXjOMKEc7FP85l3A3-HA98ma0UFDU4AlwrEqXYbf9QFO-CNeIoLkX6A5e73XJ1H_3-rGhJTivkX3ZHXXKCk9Tizd7TWk-J8ZLSxXjLusJJrZHg_l8k1Ego89r9MPnAdk2JjB45dhawS-8jc1zFczyEaNtpimRXw_eOGuzEFz0TDeASGuK-WjPMMOSTJoD9wp-dIYubhdO5RpXbcAcQu3x0UnJPjIbUzSntmt2GNTPOE2yxtF6_VKISUHJKThRHQtYx9ePTmDyFTlLOTRI8KCuOtUYOnIHZIAtNuUrjRoJ1RPcWpgkzwQ',  # noqa: E501
        'eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIiwia2lkIjoiYmFyLmNvbSJ9.eyJpc3MiOiJyZXN0eSIsInN1YiI6ImZvbyJ9.0hkDQT1lnMoGjweZeJDeSfVMllhzlmYtSqErpeU5pp7TK5OkIoLeMCSHjqYdCOwwha8znK6hBxKO-LzT4PPuhe0LnNb_qZpEbtoX6ldN8LSkhCv3Jr8lwt_hs09-lHXxdrknuYmooICI6Q66QzOpTSF4j867UwUYtfVsMpfofxpiRCJOOvynpquYGbgXc59SGJjM5wPAgYo782uRErnRFX7YJmwt5wINjvsKhr0Ry512w_EC--jDGEpcWaNKMDXKL0UMQXWoOM5IlUMA7Kr2bF966X2xuUdRnJinVGnJvdK8yKyZg_qPA26OygLeJUqF-R4jVC-lYEfte7EOLpYBBQ',  # noqa: E501
        'eyJ0eXAiOiJKV1QiLCJraWQiOiJmb28uY29tIn0=.eyJpc3MiOiJyZXN0eSIsInN1YiI6ImZvbyJ9.0hkDQT1lnMoGjweZeJDeSfVMllhzlmYtSqErpeU5pp7TK5OkIoLeMCSHjqYdCOwwha8znK6hBxKO-LzT4PPuhe0LnNb_qZpEbtoX6ldN8LSkhCv3Jr8lwt_hs09-lHXxdrknuYmooICI6Q66QzOpTSF4j867UwUYtfVsMpfofxpiRCJOOvynpquYGbgXc59SGJjM5wPAgYo782uRErnRFX7YJmwt5wINjvsKhr0Ry512w_EC--jDGEpcWaNKMDXKL0UMQXWoOM5IlUMA7Kr2bF966X2xuUdRnJinVGnJvdK8yKyZg_qPA26OygLeJUqF-R4jVC-lYEfte7EOLpYBBQ',  # noqa: E501
    ),
    ids=(
        'malformed',
        'key_mismatch',
        'iss_mismatch',
        'kid_mismatch',
        'wrong_algorithm',
        'missing_alg',
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