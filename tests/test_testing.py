import pytest

from flask_resty.testing import assert_value

# -----------------------------------------------------------------------------


def test_simple_cases():
    assert_value(1, 1)

    a = object()
    assert_value(a, a)

    assert_value('a', 'a')

    assert_value([1, 2], [1, 2])

    assert_value({1, 2}, {2, 1})


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
        assert_value(1.001, 1.002)


def test_objects():
    complex_object = {
        'a': 1,
        'b': [1, 2, 3],
        'c': [{}, {'a': 1}],
        'd': {
            'a': 1,
            'b': []
        },
    }

    assert_value(complex_object, complex_object)

    assert_value(complex_object, {})

    assert_value(complex_object, {'a': 1})

    assert_value(complex_object, {
        'b': [1, 2, 3],
        'c': [{}, {}],
    })

    assert_value(complex_object, {
        'd': {
            'a': 1,
        }
    })

    with pytest.raises(AssertionError):
        assert_value(complex_object, [])

    with pytest.raises(AssertionError):
        assert_value(complex_object, None)

    with pytest.raises(AssertionError):
        assert_value(complex_object, {
            'b': [1, 2]
        })

    with pytest.raises(AssertionError):
        assert_value(complex_object, {
            'a': 1,
            'foo': 1
        })

    with pytest.raises(AssertionError):
        assert_value(complex_object, {
            'c': [{}, {'b': 2}],
        })

    with pytest.raises(AssertionError):
        assert_value(complex_object, {
            'b': [1, 2, 3, 4],
        })
