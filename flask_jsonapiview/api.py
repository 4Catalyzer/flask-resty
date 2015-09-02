import flask

__all__ = ('Api',)

# -----------------------------------------------------------------------------


class Api(object):
    def __init__(self, app):
        self._app = app

    def init_app(self, app):
        raise NotImplementedError()

    def add_resource(self, base_rule, base_view,
                     alternate_rule=None, alternate_view=None):
        endpoint = self._get_endpoint(base_view, alternate_view)
        base_view_func = base_view.as_view(endpoint)

        if not alternate_rule:
            self._app.add_url_rule(base_rule, view_func=base_view_func)
            return

        alternate_view_func = alternate_view.as_view(endpoint)

        def view_func(*args, **kwargs):
            if flask.request.url_rule.rule == base_rule:
                return base_view_func(*args, **kwargs)
            else:
                return alternate_view_func(*args, **kwargs)

        self._app.add_url_rule(
            base_rule, view_func=view_func, endpoint=endpoint,
            methods=base_view.methods
        )
        self._app.add_url_rule(
            alternate_rule, view_func=view_func, endpoint=endpoint,
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
        @self._app.route(rule)
        def ping():
            return '', 200
