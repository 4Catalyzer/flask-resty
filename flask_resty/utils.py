def if_none(value, default):
    if value is None:
        return default

    return value


# -----------------------------------------------------------------------------


def iter_validation_errors(errors, path=()):
    if isinstance(errors, dict):
        for field_key, field_errors in errors.items():
            field_path = path + (field_key,)
            for error in iter_validation_errors(field_errors, field_path):
                yield error
    else:
        for message in errors:
            yield (message, path)


# -----------------------------------------------------------------------------


class SettableProperty(object):
    def __init__(self, get_default):
        self.get_default = get_default
        self.internal_field_name = '_' + get_default.__name__
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


settable_property = SettableProperty
