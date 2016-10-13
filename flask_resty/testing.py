import json

from .compat import zip_longest

# -----------------------------------------------------------------------------

NO_DATA = object()

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
    if isinstance(expected, dict):
        assert isinstance(actual, dict)
        for k, v in expected.items():
            assert_value(actual.get(k, None), v)
    elif isinstance(expected, list):
        assert isinstance(actual, list)
        for a, e in zip_longest(actual, expected):
            assert_value(a, e)
    elif isinstance(expected, float):
        assert abs(actual / expected - 1) < 1e-6
    else:
        assert actual == expected


def assert_response(response, expected_status_code, expected_data=NO_DATA):
    """Assert on the status and contents of a response.

    If specified, expected_data is checked against either the data or the
    errors in the response body, depending on the response status. This check
    ignores extra keys in the response contents.
    """
    assert response.status_code == expected_status_code

    if expected_data == NO_DATA:
        return

    if 200 <= response.status_code < 300:
        response_data = get_data(response)
    else:
        response_data = get_errors(response)

    assert_value(response_data, expected_data)
