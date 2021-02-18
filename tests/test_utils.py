import copy

from flask_resty.utils import UNDEFINED, SettableProperty, settable_property

# -----------------------------------------------------------------------------


def test_settable_property():
    class Foo:
        @settable_property
        def value(self):
            return 3

    assert isinstance(Foo.value, SettableProperty)

    foo = Foo()
    assert foo.value == 3

    foo.value = 4
    assert foo.value == 4

    foo.value = 5
    assert foo.value == 5

    del foo.value
    assert foo.value == 3

    del foo.value
    assert foo.value == 3

    foo.value = 6
    assert foo.value == 6


def test_undefined():
    assert bool(UNDEFINED) is False
    assert copy.copy(UNDEFINED) is UNDEFINED
    d = {"foo": UNDEFINED}
    d_deepcopy = copy.deepcopy(d)
    assert d["foo"] is d_deepcopy["foo"]
