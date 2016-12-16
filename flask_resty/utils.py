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
