import json

try:
    from itertools import zip_longest
except ImportError:
    from itertools import izip_longest as zip_longest

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
        for k, v in expected.items():
            assert_value(actual.get(k, None), v)
    elif isinstance(expected, list):
        for a, e in zip_longest(actual, expected):
            assert_value(a, e)
    elif isinstance(expected, float):
        assert abs(actual / expected - 1) < 1e-6
    else:
        assert actual == expected


def assert_response(response, expected_status=200, expected_data=NO_DATA):
    """check the results of a response. The data is checked against either the
    data or the errors in the body, depending on the expected status. It is
    allowed for the data to have more keys than the one specified"""
    assert response.status_code == expected_status

    if expected_data == NO_DATA:
        return

    if 200 <= response.status_code < 300:
        response_data = get_data(response)
    else:
        response_data = get_errors(response)

    assert_value(response_data, expected_data)
