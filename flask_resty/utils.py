"""Internal utility helpers."""

# UNDEFINED is a singleton; ensure that it is falsy and returns the same instance when copied
class _Undefined:
    def __bool__(self):
        return False

    def __copy__(self):
        return self

    def __deepcopy__(self, _):
        return self

    def __repr__(self):
        return "<UNDEFINED>"


UNDEFINED = _Undefined()

# -----------------------------------------------------------------------------


def if_none(value, default):
    if value is None:
        return default

    return value


# -----------------------------------------------------------------------------


def iter_validation_errors(errors, path=()):
    if isinstance(errors, dict):
        for field_key, field_errors in errors.items():
            field_path = path + (field_key,)
            yield from iter_validation_errors(field_errors, field_path)
    else:
        for message in errors:
            yield (message, path)


# -----------------------------------------------------------------------------


class SettableProperty:
    def __init__(self, get_default):
        self.get_default = get_default
        self.internal_field_name = "_" + get_default.__name__
        self.__doc__ = get_default.__doc__

    def __get__(self, instance, owner):
        if instance is None:
            return self
        try:
            return getattr(instance, self.internal_field_name)
        except AttributeError:
            return self.get_default(instance)

    def __set__(self, instance, value):
        setattr(instance, self.internal_field_name, value)

    def __delete__(self, instance):
        try:
            delattr(instance, self.internal_field_name)
        except AttributeError:
            pass


#: A property that can be set to a different value on the instance.
settable_property = SettableProperty
