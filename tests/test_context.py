import pytest

from flask_resty import context

# -----------------------------------------------------------------------------


def test_view_default(app):
    with app.test_request_context():
        view_1 = object()
        view_2 = object()

        assert context.get_for_view(view_1, "foo", "missing") == "missing"

        context.set_for_view(view_1, "foo", "present")

        assert context.get_for_view(view_1, "foo", "missing") == "present"
        assert context.get_for_view(view_2, "foo", "missing") == "missing"


def test_get_without_request():
    with pytest.raises(RuntimeError, match="outside of request context"):
        context.get("foo")
