from flask_resty.utils import settable_property, SettableProperty

# -----------------------------------------------------------------------------


def test_settable_property():
    class Foo(object):
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
