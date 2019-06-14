import pytest

from flask_resty import Api
from flask_resty.testing import assert_response

# -----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def routes(app):
    api = Api(app, "/api")
    api.add_ping("/ping")


# -----------------------------------------------------------------------------


def test_ping(base_client):
    response = base_client.get("/ping")
    assert_response(response, 200)
    assert response.get_data(as_text=True) == ""
