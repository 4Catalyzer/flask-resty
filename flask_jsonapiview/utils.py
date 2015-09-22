__all__ = ('if_none',)

# -----------------------------------------------------------------------------


def if_none(value, default):
    if value is None:
        return default

    return value
