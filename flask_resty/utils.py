from datetime import tzinfo, timedelta

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
            for error in iter_validation_errors(field_errors, field_path):
                yield error
    else:
        for message in errors:
            yield (message, path)


# -----------------------------------------------------------------------------

# This example is taken from
# https://docs.python.org/2/library/datetime.html#datetime.tzinfo.fromutc

ZERO = timedelta(0)

HOUR = timedelta(hours=1)


class UTC(tzinfo):
    """Python 2 and 3 compatible definition of UTC timezone"""

    def utcoffset(self, dt):
        return ZERO

    def dst(self, dt):
        return ZERO


utc = UTC()
