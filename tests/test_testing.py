import flask
import pytest

from flask_resty.testing import (
    UNDEFINED,
    InstanceOf,
    Matching,
    Predicate,
    Shape,
    assert_response,
    assert_shape,
    get_body,
)

# -----------------------------------------------------------------------------

# the two different flavors of shape should behave in the same way. Here we
# normalize the way they are called so we can parametrize the tests


def assert_shape_func_1(a, b):
    assert a == Shape(b)


assert_shape_func_2 = assert_shape

parametrize_shape_funcs = pytest.mark.parametrize(
    "assert_shape_func", (assert_shape_func_1, assert_shape_func_2)
)

# -----------------------------------------------------------------------------


@parametrize_shape_funcs
def test_shape_basic(assert_shape_func):
    assert_shape_func(1, 1)

    a = object()
    assert_shape_func(a, a)

    assert_shape_func("a", "a")

    assert_shape_func([1, 2], [1, 2])

    assert_shape_func({1, 2}, {2, 1})

    assert_shape_func(0.1 + 0.2, 0.3)


@parametrize_shape_funcs
def test_shape_failures(assert_shape_func):
    with pytest.raises(AssertionError):
        assert_shape_func({}, [])

    with pytest.raises(AssertionError):
        assert_shape_func({}, None)

    with pytest.raises(AssertionError):
        assert_shape_func(1, "1")

    with pytest.raises(AssertionError):
        assert_shape_func([1, 2], [2, 1])

    with pytest.raises(AssertionError):
        assert_shape_func([1], [1, 2])

    with pytest.raises(AssertionError):
        assert_shape_func(1.001, 1.002)


@parametrize_shape_funcs
def test_shape_mapping(assert_shape_func):
    actual_mapping = {
        "a": 1,
        "b": [1, 2, 3],
        "c": [{}, {"a": 1}],
        "d": {"a": 1, "b": []},
        "bar": "a long string",
    }

    assert_shape_func(actual_mapping, actual_mapping)

    assert_shape_func(actual_mapping, {})

    assert_shape_func(actual_mapping, {"a": 1})

    assert_shape_func(actual_mapping, {"b": [1, 2, 3], "c": [{}, {}]})

    assert_shape_func(actual_mapping, {"d": {"a": 1}})

    assert_shape_func(actual_mapping, {"foo": UNDEFINED})

    assert_shape_func(actual_mapping, {"b": InstanceOf(list)})

    assert_shape_func(actual_mapping, {"bar": Matching(r".*long.*")})

    with pytest.raises(AssertionError):
        assert_shape_func(actual_mapping, [])

    with pytest.raises(AssertionError):
        assert_shape_func(actual_mapping, None)

    with pytest.raises(AssertionError):
        assert_shape_func(actual_mapping, {"b": [1, 2]})

    with pytest.raises(AssertionError):
        assert_shape_func(actual_mapping, {"a": 1, "foo": None})

    with pytest.raises(AssertionError):
        assert_shape_func(actual_mapping, {"c": [{}, {"b": 2}]})

    with pytest.raises(AssertionError):
        assert_shape_func(actual_mapping, {"b": [1, 2, 3, 4]})

    with pytest.raises(AssertionError):
        assert_shape_func(actual_mapping, {"a": UNDEFINED})

    with pytest.raises(AssertionError):
        assert_shape_func(actual_mapping, {"bar": Matching(r".*lung.*")})


def test_predicate():
    Integer = Predicate(lambda x: isinstance(x, int))

    assert Integer == 1
    assert Integer != 1.2


def test_assert_response_with_shape(app):
    data = {"foo": "bar"}

    with app.test_request_context():
        response = flask.jsonify(data=data)

    response_data = assert_response(response, 200, Shape(data))
    assert response_data == data


def test_assert_response_returns_data(app):
    data = {"foo": "bar"}

    with app.test_request_context():
        response = flask.jsonify(data=data)

    response_data = assert_response(response, 200)
    assert response_data == data


def test_assert_response_returns_errors(app):
    errors = [{"code": "bar"}]

    with app.test_request_context():
        response = flask.make_response(flask.jsonify(errors=errors), 400)

    response_errors = assert_response(response, 400)
    assert response_errors == errors


def test_assert_response_on_redirect(app):
    with app.test_request_context():
        response = flask.redirect("/foo")

    assert_response(response, 302)


def test_assert_response_returns_custom_data(app):
    data = {"foo": "bar"}

    with app.test_request_context():
        response = flask.jsonify(data)

    response_data = assert_response(response, 200, get_data=get_body)
    assert response_data == data


def test_assert_response_returns_custom_errors(app):
    errors = [{"code": "bar"}]

    with app.test_request_context():
        response = flask.make_response(flask.jsonify(errors), 400)

    response_errors = assert_response(response, 400, get_errors=get_body)
    assert response_errors == errors
