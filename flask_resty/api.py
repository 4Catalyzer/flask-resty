import posixpath

import flask

from .exceptions import ApiError

# -----------------------------------------------------------------------------

# Don't set default value in function so we can assert on None-ness.
DEFAULT_ID_RULE = '<id>'

# -----------------------------------------------------------------------------


class Api(object):
    def __init__(self, app=None, prefix=''):
        if app:
            self._app = app
            self.init_app(app)

        self._prefix = prefix

    def init_app(self, app):
        app.extensions['resty'] = FlaskRestyState(self)

        @app.errorhandler(ApiError)
        def handle_api_error(error):
            return flask.jsonify(**error.body), error.status_code

    def _get_app(self, app):
        app = app or self._app
        assert app, "no application specified"
        return app

    def add_resource(
        self, base_rule, base_view, alternate_view=None,
        alternate_rule=None, id_rule=None, app=None,
    ):
        if alternate_view:
            if not alternate_rule:
                id_rule = id_rule or DEFAULT_ID_RULE
                alternate_rule = posixpath.join(base_rule, id_rule)
            else:
                assert id_rule is None
        else:
            assert alternate_rule is None
            assert id_rule is None

        app = self._get_app(app)
        endpoint = self._get_endpoint(base_view, alternate_view)

        # Store the view urls for reference. Doesn't support multiple routes
        # mapped to same view.
        views = app.extensions['resty'].views

        base_rule_full = '{}{}'.format(self._prefix, base_rule)
        base_view_func = base_view.as_view(endpoint)

        if not alternate_view:
            app.add_url_rule(base_rule_full, view_func=base_view_func)
            views[base_view] = Resource(base_view, base_rule_full)
            return

        alternate_rule_full = '{}{}'.format(self._prefix, alternate_rule)
        alternate_view_func = alternate_view.as_view(endpoint)

        def view_func(*args, **kwargs):
            if flask.request.url_rule.rule == base_rule_full:
                return base_view_func(*args, **kwargs)
            else:
                return alternate_view_func(*args, **kwargs)

        app.add_url_rule(
            base_rule_full, view_func=view_func, endpoint=endpoint,
            methods=base_view.methods,
        )
        app.add_url_rule(
            alternate_rule_full, view_func=view_func, endpoint=endpoint,
            methods=alternate_view.methods,
        )

        views[base_view] = Resource(base_view, base_rule_full)
        views[alternate_view] = Resource(alternate_view, alternate_rule_full)

    def _get_endpoint(self, base_view, alternate_view):
        base_view_name = base_view.__name__
        if not alternate_view:
            return base_view_name

        alternate_view_name = alternate_view.__name__
        if len(alternate_view_name) < len(base_view_name):
            return alternate_view_name
        else:
            return base_view_name

    def add_ping(self, rule, app=None):
        app = self._get_app(app)

        # Note that unlike actual API paths, this doesn't use the prefix.
        @app.route(rule)
        def ping():
            return '', 200


# -----------------------------------------------------------------------------


class FlaskRestyState(object):
    def __init__(self, api):
        self.api = api
        self.views = {}


class Resource(object):
    """Simple object to store information about an added resource"""

    def __init__(self, view, rule):
        self.rule = rule
        self.view = view
