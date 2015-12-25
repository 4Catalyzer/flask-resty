import re

RE_SWAGGER_URL = re.compile(r'<(?:[^:<>]+:)?([^<>]+)>')
MARSHMALLOW_PLUGIN_NAME = 'apispec.ext.marshmallow'
RESTY_PLUGIN_NAME = 'resty'


def ref(schema_name, path='definitions'):
    """Generate a ref object"""
    return {'$ref': '#/{}/{}'.format(path, schema_name)}


def flask_path_to_swagger(path):
    """Convert a Flask URL rule to a Swagger-compliant path.
    :param str path: Flask path template.
    """
    return RE_SWAGGER_URL.sub(r'{\1}', path)


def get_marshmallow_schema_name(spec, schema):
    """Bridge to the marshmallow plugin to get the
    schema name. If the schema doesn't exist, create one"""
    try:
        return spec.plugins[MARSHMALLOW_PLUGIN_NAME]['refs'][schema]
    except KeyError:
        spec.definition(schema.__name__, schema=schema)
        return schema.__name__


def get_state(app):
    """Gets the flask-resty state for the application"""
    assert RESTY_PLUGIN_NAME in app.extensions, \
        'flask-resty was not registered to the current application'
    return app.extensions[RESTY_PLUGIN_NAME]
