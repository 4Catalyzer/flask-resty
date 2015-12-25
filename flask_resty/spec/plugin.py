from collections import defaultdict

from flask import current_app

from .operation import Operation
from .utils import flask_path_to_swagger, get_state

rules = {}


def schema_path_helper(spec, path, view, **kwargs):
    """Path helper that uses resty views
    :param view: an `ApiView` object
    """

    resource = get_state(current_app).views[view]
    rule = rules[resource.rule]

    operations = defaultdict(Operation)
    view_instance = view()
    view_instance.spec_declaration(view, operations, spec)

    # add path arguments
    parameters = []
    for arg in rule.arguments:
        parameters.append({
            'name': arg,
            'in': 'path',
            'required': True,
            'type': 'string',
        })
    if parameters:
        path['parameters'] = parameters

    path.path = flask_path_to_swagger(resource.rule)
    path.operations = dict(**operations)


def setup(spec):
    """Setup for the marshmallow plugin."""
    spec.register_path_helper(schema_path_helper)
    global rules
    rules = {
        rule.rule: rule for rule in current_app.url_map.iter_rules()
    }
