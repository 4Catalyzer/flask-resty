import marshmallow

# -----------------------------------------------------------------------------

MA2 = int(marshmallow.__version__[0]) == 2

# -----------------------------------------------------------------------------


def _strict_run(method, obj_or_data, **kwargs):
    result = method(obj_or_data, **kwargs)
    if MA2:  # Make marshmallow 2 schemas behave like marshmallow 3
        data, errors = result
        if errors:
            raise marshmallow.ValidationError(errors, data=data)
    else:
        data = result

    return data


def schema_load(schema, in_data, **kwargs):
    return _strict_run(schema.load, in_data, **kwargs)


def schema_dump(schema, obj, **kwargs):
    return _strict_run(schema.dump, obj, **kwargs)
