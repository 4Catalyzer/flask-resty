from flask.ext.resty import Api
import pytest

# -----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def routes(app):
    api = Api(app, '/api')
    api.add_ping('/ping')


# -----------------------------------------------------------------------------


def test_ping(client):
    response = client.get('/ping')
    assert response.status_code == 200
    assert not response.data
