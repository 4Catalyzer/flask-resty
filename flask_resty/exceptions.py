import traceback

import flask
from werkzeug.exceptions import default_exceptions

# -----------------------------------------------------------------------------


class ApiError(Exception):
    def __init__(self, status_code, *errors):
        self.status_code = status_code
        self.body = {
            'errors': errors or self.get_default_errors(status_code),
        }

        if flask.current_app.debug or flask.current_app.testing:
            self.body['debug'] = traceback.format_exc()

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
            'code': '_'.join(word.lower() for word in exc.name.split()),
            'details': exc.description,
        }

    def update(self, additional):
        for error in self.body['errors']:
            error.update(additional)

        # Allow e.g. `raise e.update(additional)`.
        return self

    @property
    def response(self):
        if flask.current_app.config.get('RESTY_TRAP_API_ERRORS'):
            raise self

        return flask.jsonify(self.body), self.status_code
