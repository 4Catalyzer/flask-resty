import flask
import functools
import posixpath
from werkzeug.exceptions import HTTPException

from .exceptions import ApiError

# -----------------------------------------------------------------------------

# Don't set default value in function so we can assert on None-ness.
DEFAULT_ID_RULE = "<id>"

# -----------------------------------------------------------------------------


def handle_api_error(error):
    return error.response


def handle_http_exception(error):
    return ApiError.from_http_exception(error).response


# -----------------------------------------------------------------------------


class Api:
    """The Api object controls the Flask-RESTy extension.

    This can either be bound to an individual Flask application passed in
    at initialization, or to multiple applications via :py:meth:`init_app`.

    After initializing an application, use this object to register resources
    with :py:meth:`add_resource`, either to the bound application by default
    or to an explicitly-specified application object via the `app` keyword
    argument. Use :py:meth:`add_ping` to add a ping endpoint for health checks.

    Once registered, Flask-RESTy will convert all HTTP errors thrown by the
    application to JSON.

    By default your API will be rooted at '/'. Pass `prefix` to specify a
    custom root.

    :param app: The Flask application object.
    :type app: :py:class:`flask.Flask`
    :param str prefix: The API path prefix.
    """

    def __init__(self, app=None, prefix=""):
        if app:
            self._app = app
            self.init_app(app)
        else:
            self._app = None

        self.prefix = prefix

    def init_app(self, app):
        """Initialize an application for use with Flask-RESTy.

        :param app: The Flask application object.
        :type app: :py:class:`flask.Flask`
        """
        app.extensions["resty"] = FlaskRestyState(self)

        app.register_error_handler(ApiError, handle_api_error)
        app.register_error_handler(HTTPException, handle_http_exception)

    def _get_app(self, app):
        app = app or self._app
        assert app, "no application specified"
        return app

    def add_resource(
        self,
        base_rule,
        base_view,
        alternate_view=None,
        *,
        alternate_rule=None,
        id_rule=None,
        app=None,
    ):
        """Add a REST resource.

        :param str base_rule: The URL rule for the resource. This will be
            prefixed by the API prefix.
        :param ApiView base_view: Class-based view for the resource.
        :param ApiView alternate_view: If specified, an alternate
            class-based view for the resource. Usually, this will be a detail
            view, when the base view is a list view.
        :param alternate_rule: If specified, the URL rule for the alternate
            view. This will be prefixed by the API prefix. This is mutually
            exclusive with `id_rule`, and must not be specified if
            `alternate_view` is not specified.
        :type alternate_rule: str or None
        :param id_rule: If specified, a suffix to append to `base_rule` to get
            the alternate view URL rule. If `alternate_view` is specified, and
            `alternate_rule` is not, then this defaults to '<id>'. This is
            mutually exclusive with `alternate_rule`, and must not be specified
            if `alternate_view` is not specified.
        :type id_rule: str or None
        :param app: If specified, the application to which to add
            the route(s). Otherwise, this will be the bound application, if
            present.
        :type app: :py:class:`flask.Flask`
        :raises AssertionError: If no Flask application is bound or specified.
        """
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

        base_rule_full = f"{self.prefix}{base_rule}"
        base_view_func = base_view.as_view(endpoint)

        if not alternate_view:
            app.add_url_rule(base_rule_full, view_func=base_view_func)
            return

        alternate_rule_full = f"{self.prefix}{alternate_rule}"
        alternate_view_func = alternate_view.as_view(endpoint)

        @functools.wraps(base_view_func)
        def view_func(*args, **kwargs):
            if flask.request.url_rule.rule == base_rule_full:
                return base_view_func(*args, **kwargs)
            else:
                return alternate_view_func(*args, **kwargs)

        app.add_url_rule(
            base_rule_full,
            view_func=view_func,
            endpoint=endpoint,
            methods=base_view.methods,
        )
        app.add_url_rule(
            alternate_rule_full,
            view_func=view_func,
            endpoint=endpoint,
            methods=alternate_view.methods,
        )

    def _get_endpoint(self, base_view, alternate_view):
        base_view_name = base_view.__name__
        if not alternate_view:
            return base_view_name

        alternate_view_name = alternate_view.__name__
        if len(alternate_view_name) < len(base_view_name):
            return alternate_view_name
        else:
            return base_view_name

    def add_ping(self, rule, *, status_code=200, app=None):
        """Add a ping route.

        :param str rule: The URL rule. This will not use the API prefix, as the
            ping endpoint is not really part of the API.
        :param int status_code: The ping response status code. The default is
            200 rather than the more correct 204 because many health checks
            look for 200s.
        :param app: If specified, the application to which to add the route.
            Otherwise, this will be the bound application, if present.
        :type app: :py:class:`flask.Flask`
        :raises AssertionError: If no Flask application is bound or specified.
        """
        app = self._get_app(app)

        @app.route(rule)
        def ping():
            return "", status_code


# -----------------------------------------------------------------------------


class FlaskRestyState:
    def __init__(self, api):
        self.api = api
