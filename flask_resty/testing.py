import json
import re
from collections.abc import Mapping, Sequence

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


def assert_shape(actual, expected, key=None):
    """Assert that ``actual`` and ``expected`` have the same data shape."""

    suffix = ""

    if key is not None:
        suffix = (
            " for parent "
            + ("index" if isinstance(key, int) else "key")
            + f" {key!r}"
        )

    if isinstance(expected, Mapping):
        assert isinstance(actual, Mapping)
        # Unlike all the others, this checks that the actual items are a
        # superset of the expected items, rather than that they match.
        for key, value in expected.items():
            if value is not UNDEFINED:
                assert key in actual, (
                    f"expected key {key!r} not found in: {actual!r}" + suffix
                )

                assert_shape(actual[key], value, key=key)
            else:
                assert key not in actual, (
                    f"expected key {key!r} not found in: {actual!r}" + suffix
                )
    elif isinstance(expected, (str, bytes)):
        assert expected == actual
    elif isinstance(expected, Sequence):
        assert isinstance(actual, Sequence), (
            f"{actual!r} is not a Sequence" + suffix
        )

        actual_len = len(actual)
        expected_len = len(expected)

        assert actual_len == expected_len, (
            "expected sequences to be the same length but "
            + (
                f"the actual value has {actual_len - expected_len} more items"
                if actual_len > expected_len
                else f"the actual value has {expected_len - actual_len} less items"
            )
            + suffix
        )
        for idx, (actual_item, expected_item) in enumerate(
            zip(actual, expected)
        ):
            assert_shape(actual_item, expected_item, key=idx)
    elif isinstance(expected, float):
        assert (
            abs(actual - expected) < 1e-6
        ), "float not within the allowed tolerance of 1e-6"
    else:
        assert expected == actual, (
            f"{actual!r} is not equal to {expected!r}" + suffix
        )


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

    if not response.content_length:
        response_data = UNDEFINED
    elif 200 <= response.status_code < 300:
        response_data = get_data(response)
    elif response.status_code >= 400:
        response_data = get_errors(response)
    else:
        response_data = response.data

    status_code = response.status_code

    assert (
        status_code == expected_status_code
    ), f"expected status code {expected_status_code!r}, got {status_code!r}"

    if expected_data is not UNDEFINED:
        if not isinstance(expected_data, Predicate):
            expected_data = Shape(expected_data)

        assert response_data == expected_data

    return response_data
