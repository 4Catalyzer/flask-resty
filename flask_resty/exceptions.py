import flask
import traceback
from werkzeug.exceptions import default_exceptions

from .utils import iter_validation_errors

# -----------------------------------------------------------------------------


class ApiError(Exception):
    """An API exception.

    When raised, Flask-RESTy will send an HTTP response with the provided
    `status_code` and the provided `errors` under the ``errors`` property as
    JSON.

    If :py:attr:`flask.Flask.debug` or :py:attr:`flask.Flask.testing` is True,
    the body will also contain the full traceback under the ``debug`` property.

    :param int status_code: The HTTP status code for the error response.
    :param dict errors: A list of dict with error data.
    """

    def __init__(self, status_code, *errors):
        self.status_code = status_code
        self.body = {"errors": errors or self.get_default_errors(status_code)}

        if flask.current_app.debug or flask.current_app.testing:
            self.body["debug"] = traceback.format_exc()

    @classmethod
    def from_http_exception(cls, exc):
        return cls(exc.code, cls.get_error_from_http_exception(exc))

    @classmethod
    def get_default_errors(cls, status_code):
        if status_code not in default_exceptions:
            return ()

        exc = default_exceptions[status_code]()
        return (cls.get_error_from_http_exception(exc),)

    @classmethod
    def get_error_from_http_exception(cls, exc):
        return {
            "code": "_".join(word.lower() for word in exc.name.split()),
            "detail": exc.description,
        }

    @classmethod
    def from_validation_error(
        cls, status_code, error, format_validation_error
    ):
        return cls(
            status_code,
            *(
                format_validation_error(message, path)
                for message, path in iter_validation_errors(error.messages)
            ),
        )

    def update(self, additional):
        """Add additional metadata to the error.

        Can be chained with further updates.

        :param dict additional: The additional metadata
        :return: The :py:class:`ApiError` that :py:meth:`update` was called on
        :rtype: :py:class:`ApiError`
        """
        for error in self.body["errors"]:
            error.update(additional)

        # Allow e.g. `raise e.update(additional)`.
        return self

    @property
    def response(self):
        if flask.current_app.config.get("RESTY_TRAP_API_ERRORS"):
            raise self

        return flask.jsonify(self.body), self.status_code
