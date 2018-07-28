from collections import defaultdict

from apispec.ext.flask import FlaskPlugin
from apispec.ext.marshmallow import MarshmallowPlugin
import flask

from .operation import Operation

# -----------------------------------------------------------------------------

RESTY_PLUGIN_NAME = 'resty'

# -----------------------------------------------------------------------------


class FlaskRestyPlugin(MarshmallowPlugin):
    def __init__(self, *args, **kwargs):
        super(FlaskRestyPlugin, self).__init__(*args, **kwargs)

        self._rules = {
            rule.rule: rule for rule in flask.current_app.url_map.iter_rules()
        }

    def path_helper(self, path, view, **kwargs):
        """Path helper for Flask-RESTy views.

        :param view: An `ApiView` object.
        """
        super(FlaskRestyPlugin, self).path_helper(
            path=path,
            view=view,
            **kwargs
        )

        resource = self.get_state().views[view]
        rule = self._rules[resource.rule]

        operations = defaultdict(Operation)
        view_instance = view()
        view_instance.spec_declaration(view, operations, self)

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
            operations['parameters'] = parameters

        path.path = FlaskPlugin.flaskpath2openapi(resource.rule)
        path.operations = dict(**operations)

    def get_state(self):
        app = flask.current_app
        assert RESTY_PLUGIN_NAME in app.extensions, (
            "Flask-RESTy was not registered to the current application"
        )

        return app.extensions[RESTY_PLUGIN_NAME]
