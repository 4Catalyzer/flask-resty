from . import context

# -----------------------------------------------------------------------------

REQUEST_CREDENTIALS_KEY = 'request_credentials'

# -----------------------------------------------------------------------------


def get_request_credentials():
    return context.get_context_value(REQUEST_CREDENTIALS_KEY, None)


def set_request_credentials(credentials):
    context.set_context_value(REQUEST_CREDENTIALS_KEY, credentials)


# -----------------------------------------------------------------------------


class AuthenticationBase(object):
    """Base class for the API authentication scheme. Flask-RESTy provides an
    implementation using `JSON Web Tokens`_  but you can use any authentication
    scheme by extending :py:class:`AuthenticationBase` and implementing
    :py:meth:`get_request_credentials`.

    .. _JSON Web Tokens: https://jwt.io/
    """
    def authenticate_request(self):
        """Stores the request credentials in the
        :py:class:`flask.ctx.AppContext`.

        .. warning::

            No validation is performed by Flask-RESTy. It is up to the implementor
            to validate the request in :py:meth:`get_request_credentials`.
        """
        set_request_credentials(self.get_request_credentials())

    def get_request_credentials(self):
        """Retrieve the credentials from the current request. Typically this
        is done by inspecting :py:data:`flask.request`.

        .. warning::

            Implementing classes **must** raise an exception on authentication
            failure. A 401 Unauthorized :py:class:`ApiError` is recommended.
        """
        raise NotImplementedError()


# -----------------------------------------------------------------------------


class NoOpAuthentication(object):
    """An authentication scheme that always allows the request.
    """
    def authenticate_request(self):
        pass
