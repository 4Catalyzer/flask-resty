import traceback

import flask

# -----------------------------------------------------------------------------


class ApiError(Exception):
    """An API exception. When raised, Flask-RESTy will send an HTTP response with
    the provided `status_code`. The JSON encoded body contains a list of the
    provided `errors` nested under a key named ``errors``.

    If :py:attr:`flask.Flask.debug` or :py:attr:`flask.Flask.testing` is True,
    the body will also contain the full traceback under a key named ``debug``.

    :param int status_code: The HTTP status code for the error response
    :param list errors: A list of dict with error metadata
    """
    def __init__(self, status_code, *errors):
        self.status_code = status_code
        self.body = {
            'errors': errors,
        }

        if flask.current_app.debug or flask.current_app.testing:
            self.body['debug'] = traceback.format_exc()

    def update(self, additional):
        """Add additional metadata to each error. Can be chained with
        further updates.

        :param dict additional: The additional metadata
        :return: The :py:class:`ApiError` that :py:meth:`update` was called on
        :rtype: :py:class:`ApiError`
        """
        for error in self.body['errors']:
            error.update(additional)

        # Allow e.g. `raise e.update(additional)`.
        return self
