from collections import Mapping, Sequence
import json

from .compat import basestring

# -----------------------------------------------------------------------------

UNDEFINED = object()

# -----------------------------------------------------------------------------


def get_body(response):
    assert response.mimetype == 'application/json'
    return json.loads(response.get_data(as_text=True))


def get_data(response):
    return get_body(response)['data']


def get_errors(response):
    return get_body(response)['errors']


def get_meta(response):
    return get_body(response)['meta']


def assert_value(actual, expected):
    if isinstance(expected, Mapping):
        assert isinstance(actual, Mapping)
        # Unlike all the others, this checks that the actual items are a
        # superset of the expected items, rather than that they match.
        for key, value in expected.items():
            if value is not UNDEFINED:
                assert key in actual
                assert_value(actual[key], value)
            else:
                assert key not in actual
    elif isinstance(expected, basestring):
        assert actual == expected
    elif isinstance(expected, Sequence):
        assert isinstance(actual, Sequence)
        assert len(actual) == len(expected)
        for actual_item, expected_item in zip(actual, expected):
            assert_value(actual_item, expected_item)
    elif isinstance(expected, float):
        assert abs(actual - expected) < 1e-6
    else:
        assert actual == expected


def assert_response(response, expected_status_code, expected_data=UNDEFINED):
    """Assert on the status and contents of a response.

    If specified, expected_data is checked against either the data or the
    errors in the response body, depending on the response status. This check
    ignores extra keys dictionaries in the response contents.
    """
    assert response.status_code == expected_status_code

    if expected_data == UNDEFINED:
        return

    if 200 <= response.status_code < 300:
        response_data = get_data(response)
    else:
        response_data = get_errors(response)

    assert_value(response_data, expected_data)
