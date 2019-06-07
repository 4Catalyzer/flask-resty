from . import context

# -----------------------------------------------------------------------------


def get_request_credentials():
    return context.get('request_credentials')


def set_request_credentials(credentials):
    context.set('request_credentials', credentials)


# -----------------------------------------------------------------------------


class AuthenticationBase:
    """Base class for API authentication components.

    Authentication components are responsible for extracting the request
    credentials, if any. They should raise a 401 if the credentials are
    invalid, but should provide `None` for unauthenticated users.

    Flask-RESTy provides an implementation using `JSON Web Tokens`_  but you
    can use any authentication component by extending
    :py:class:`AuthenticationBase` and implementing
    :py:meth:`get_request_credentials`.

    .. _JSON Web Tokens: https://jwt.io/
    """

    def authenticate_request(self):
        """Store the request credentials in the
        :py:class:`flask.ctx.AppContext`.

        .. warning::

            No validation is performed by Flask-RESTy. It is up to the
            implementor to validate the request in
            :py:meth:`get_request_credentials`.
        """
        set_request_credentials(self.get_request_credentials())

    def get_request_credentials(self):
        """Get the credentials for the current request.

        Typically this is done by inspecting :py:data:`flask.request`.

        .. warning::

            Implementing classes **must** raise an exception on authentication
            failure. A 401 Unauthorized :py:class:`ApiError` is recommended.
        """
        raise NotImplementedError()


# -----------------------------------------------------------------------------


class NoOpAuthentication:
    """An authentication component that provides no credentials."""

    def authenticate_request(self):
        pass
