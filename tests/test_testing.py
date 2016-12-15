from datetime import datetime, timedelta

import pytest

from flask_resty.testing import (
    assert_similar, JUST_BEFORE, Matching, Similar, UNDEFINED,
)
from flask_resty.utils import utc

# -----------------------------------------------------------------------------

# the two different flavors of similar should behave in the same way. Here we
# normalize the way they are called so we can parametrize the tests


def assert_similar_func_1(a, b):
    assert a == Similar(b)


assert_similar_func_2 = assert_similar

parametrize_similar_funcs = pytest.mark.parametrize('assert_similar_func', (
    assert_similar_func_1, assert_similar_func_2,
))

# -----------------------------------------------------------------------------


@parametrize_similar_funcs
def test_similar_basic(assert_similar_func):
    assert_similar_func(1, 1)

    a = object()
    assert_similar_func(a, a)

    assert_similar_func('a', 'a')

    assert_similar_func([1, 2], [1, 2])

    assert_similar_func({1, 2}, {2, 1})

    assert_similar_func(0.1 + 0.2, 0.3)


@parametrize_similar_funcs
def test_similar_failures(assert_similar_func):
    with pytest.raises(AssertionError):
        assert_similar_func({}, [])

    with pytest.raises(AssertionError):
        assert_similar_func({}, None)

    with pytest.raises(AssertionError):
        assert_similar_func(1, '1')

    with pytest.raises(AssertionError):
        assert_similar_func([1, 2], [2, 1])

    with pytest.raises(AssertionError):
        assert_similar_func([1], [1, 2])

    with pytest.raises(AssertionError):
        assert_similar_func(1.001, 1.002)


@parametrize_similar_funcs
def test_similar_mapping(assert_similar_func):
    actual_mapping = {
        'a': 1,
        'b': [1, 2, 3],
        'c': [{}, {'a': 1}],
        'd': {
            'a': 1,
            'b': [],
        },
        'bar': 'a long string',
    }

    assert_similar_func(actual_mapping, actual_mapping)

    assert_similar_func(actual_mapping, {})

    assert_similar_func(actual_mapping, {'a': 1})

    assert_similar_func(actual_mapping, {
        'b': [1, 2, 3],
        'c': [{}, {}],
    })

    assert_similar_func(actual_mapping, {
        'd': {
            'a': 1,
        },
    })

    assert_similar_func(actual_mapping, {
        'foo': UNDEFINED,
    })

    assert_similar_func(actual_mapping, {
        'bar': Matching(r'.*long.*')
    })

    with pytest.raises(AssertionError):
        assert_similar_func(actual_mapping, [])

    with pytest.raises(AssertionError):
        assert_similar_func(actual_mapping, None)

    with pytest.raises(AssertionError):
        assert_similar_func(actual_mapping, {
            'b': [1, 2],
        })

    with pytest.raises(AssertionError):
        assert_similar_func(actual_mapping, {
            'a': 1,
            'foo': None,
        })

    with pytest.raises(AssertionError):
        assert_similar_func(actual_mapping, {
            'c': [{}, {'b': 2}],
        })

    with pytest.raises(AssertionError):
        assert_similar_func(actual_mapping, {
            'b': [1, 2, 3, 4],
        })

    with pytest.raises(AssertionError):
        assert_similar_func(actual_mapping, {
            'a': UNDEFINED,
        })

    with pytest.raises(AssertionError):
        assert_similar_func(actual_mapping, {
            'bar': Matching(r'.*lung.*')
        })


# -----------------------------------------------------------------------------


def test_just_before():
    now = datetime.now(utc)

    assert JUST_BEFORE == now
    assert JUST_BEFORE == now - timedelta(seconds=9)

    assert JUST_BEFORE != now + timedelta(seconds=1)
    assert JUST_BEFORE != now - timedelta(seconds=10)
    assert JUST_BEFORE != now - timedelta(hours=4)

    assert JUST_BEFORE == now.isoformat()
    assert JUST_BEFORE != (now - timedelta(seconds=10)).isoformat()

    assert_similar({'foo': now}, {'foo': JUST_BEFORE})
