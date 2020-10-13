import json
import re
from collections import Mapping, Sequence
from flask.testing import FlaskClient

from .utils import UNDEFINED

# -----------------------------------------------------------------------------


class ApiClient(FlaskClient):
    """A `flask.testing.FlaskClient` with a few conveniences:

    * Prefixes paths
    * Sets ``Content-Type`` to "application/json"
    * Envelopes ``data`` within a "data" key in the request payload
    """

    def open(self, path, *args, **kwargs):
        full_path = "{}{}".format(
            self.application.extensions["resty"].api.prefix, path
        )

        if "data" in kwargs:
            kwargs.setdefault("content_type", "application/json")
            if kwargs["content_type"] == "application/json":
                kwargs["data"] = json.dumps({"data": kwargs["data"]})

        return super().open(full_path, *args, **kwargs)


# -----------------------------------------------------------------------------


class Predicate:
    """A helper object to do predicate assertion"""

    def __init__(self, predicate):
        self.predicate = predicate

    def __eq__(self, other):
        return self.predicate(other)

    def __ne__(self, other):
        return not self.predicate(other)


def InstanceOf(type):
    return Predicate(lambda value: isinstance(value, type))


def Matching(expected_regex):
    return Predicate(re.compile(expected_regex).match)


def assert_shape(actual, expected):
    """Assert that ``actual`` and ``expected`` have the same data shape."""
    if isinstance(expected, Mapping):
        assert isinstance(actual, Mapping)
        # Unlike all the others, this checks that the actual items are a
        # superset of the expected items, rather than that they match.
        for key, value in expected.items():
            if value is not UNDEFINED:
                assert key in actual
                assert_shape(actual[key], value)
            else:
                assert key not in actual
    elif isinstance(expected, (str, bytes)):
        assert expected == actual
    elif isinstance(expected, Sequence):
        assert isinstance(actual, Sequence)
        assert len(actual) == len(expected)
        for actual_item, expected_item in zip(actual, expected):
            assert_shape(actual_item, expected_item)
    elif isinstance(expected, float):
        assert abs(actual - expected) < 1e-6
    else:
        assert expected == actual


def Shape(expected):
    def predicate(actual):
        assert_shape(actual, expected)
        return True

    return Predicate(predicate)


# -----------------------------------------------------------------------------


def get_raw_body(response):
    return response.get_data(as_text=True)


def get_body(response):
    assert response.mimetype == "application/json"
    return json.loads(get_raw_body(response))


def get_data(response):
    return get_body(response)["data"]


def get_errors(response):
    return get_body(response)["errors"]


def get_meta(response):
    return get_body(response)["meta"]


def assert_response(
    response,
    expected_status_code,
    expected_data=UNDEFINED,
    *,
    get_data=get_data,
    get_errors=get_errors,
):
    """Assert on the status and contents of a response.

    If specified, expected_data is checked against either the data or the
    errors in the response body, depending on the response status. This check
    ignores extra dictionary items in the response contents.
    """
    status_code = response.status_code
    assert status_code == expected_status_code

    if not response.content_length:
        response_data = UNDEFINED
    elif 200 <= response.status_code < 300:
        response_data = get_data(response)
    elif response.status_code >= 400:
        response_data = get_errors(response)
    else:
        response_data = response.data

    if expected_data is not UNDEFINED:
        if not isinstance(expected_data, Predicate):
            expected_data = Shape(expected_data)

        assert response_data == expected_data

    return response_data
