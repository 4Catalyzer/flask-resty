import pytest

from flask_resty.testing import assert_value, UNDEFINED

# -----------------------------------------------------------------------------


def test_basic():
    assert_value(1, 1)

    a = object()
    assert_value(a, a)

    assert_value('a', 'a')

    assert_value([1, 2], [1, 2])

    assert_value({1, 2}, {2, 1})

    assert_value(0.1 + 0.2, 0.3)


def test_failures():
    with pytest.raises(AssertionError):
        assert_value({}, [])

    with pytest.raises(AssertionError):
        assert_value({}, None)

    with pytest.raises(AssertionError):
        assert_value(1, '1')

    with pytest.raises(AssertionError):
        assert_value([1, 2], [2, 1])

    with pytest.raises(AssertionError):
        assert_value([1], [1, 2])

    with pytest.raises(AssertionError):
        assert_value(1.001, 1.002)


def test_mapping():
    actual_mapping = {
        'a': 1,
        'b': [1, 2, 3],
        'c': [{}, {'a': 1}],
        'd': {
            'a': 1,
            'b': [],
        },
    }

    assert_value(actual_mapping, actual_mapping)

    assert_value(actual_mapping, {})

    assert_value(actual_mapping, {'a': 1})

    assert_value(actual_mapping, {
        'b': [1, 2, 3],
        'c': [{}, {}],
    })

    assert_value(actual_mapping, {
        'd': {
            'a': 1,
        },
    })

    assert_value(actual_mapping, {
        'foo': UNDEFINED,
    })

    with pytest.raises(AssertionError):
        assert_value(actual_mapping, [])

    with pytest.raises(AssertionError):
        assert_value(actual_mapping, None)

    with pytest.raises(AssertionError):
        assert_value(actual_mapping, {
            'b': [1, 2],
        })

    with pytest.raises(AssertionError):
        assert_value(actual_mapping, {
            'a': 1,
            'foo': None,
        })

    with pytest.raises(AssertionError):
        assert_value(actual_mapping, {
            'c': [{}, {'b': 2}],
        })

    with pytest.raises(AssertionError):
        assert_value(actual_mapping, {
            'b': [1, 2, 3, 4],
        })

    with pytest.raises(AssertionError):
        assert_value(actual_mapping, {
            'a': UNDEFINED,
        })
