import flask

__all__ = ('Api',)

# -----------------------------------------------------------------------------

# Don't set default value in function so we can assert on None-ness.
DEFAULT_ID_RULE = '<id>'

# -----------------------------------------------------------------------------


class Api(object):
    def __init__(self, app, prefix=''):
        self._app = app
        self._prefix = prefix

    def init_app(self, app):
        raise NotImplementedError()

    def add_resource(
            self, base_rule, base_view, alternate_view=None,
            alternate_rule=None, id_rule=None):
        if alternate_view:
            if not alternate_rule:
                id_rule = id_rule or DEFAULT_ID_RULE
                alternate_rule = '{}/{}'.format(base_rule, id_rule)
            else:
                assert id_rule is None
        else:
            assert alternate_rule is None
            assert id_rule is None

        endpoint = self._get_endpoint(base_view, alternate_view)

        base_rule_full = '{}{}'.format(self._prefix, base_rule)
        base_view_func = base_view.as_view(endpoint)

        if not alternate_view:
            self._app.add_url_rule(base_rule_full, view_func=base_view_func)
            return

        alternate_rule_full = '{}{}'.format(self._prefix, alternate_rule)
        alternate_view_func = alternate_view.as_view(endpoint)

        def view_func(*args, **kwargs):
            if flask.request.url_rule.rule == base_rule_full:
                return base_view_func(*args, **kwargs)
            else:
                return alternate_view_func(*args, **kwargs)

        self._app.add_url_rule(
            base_rule_full, view_func=view_func, endpoint=endpoint,
            methods=base_view.methods
        )
        self._app.add_url_rule(
            alternate_rule_full, view_func=view_func, endpoint=endpoint,
            methods=alternate_view.methods
        )

    @staticmethod
    def _get_endpoint(base_view, alternate_view):
        base_view_name = base_view.__name__
        if not alternate_view:
            return base_view_name

        alternate_view_name = alternate_view.__name__
        if len(alternate_view_name) < len(base_view_name):
            return alternate_view_name
        else:
            return base_view_name

    def add_ping(self, rule):
        # Note that unlike actual API paths, this doesn't use the prefix.
        @self._app.route(rule)
        def ping():
            return '', 200
