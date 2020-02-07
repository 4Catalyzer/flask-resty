import flask

from . import context
from .exceptions import ApiError

# -----------------------------------------------------------------------------


def get_request_credentials():
    return context.get("request_credentials")


def set_request_credentials(credentials):
    context.set("request_credentials", credentials)


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

        :return: The credentials for the current request.
        """
        raise NotImplementedError()


# -----------------------------------------------------------------------------


class NoOpAuthentication:
    """An authentication component that provides no credentials."""

    def authenticate_request(self):
        pass


# -----------------------------------------------------------------------------


class HeaderAuthenticationBase(AuthenticationBase):
    """Base class for header authentication components.

    These authentication components get their credentials from the
    ``Authorization`` request header. The Authorization header has the form::

        Authorization: <scheme> <token>

    This class also supports fallback to a query parameter, for cases where
    API clients cannot set headers.
    """

    #: Corresponds to the <scheme> in the Authorization request header.
    header_scheme = "Bearer"

    #: A fallback query parameter. The value of this query parameter will be
    #: used as credentials if the Authorization request header is missing.
    credentials_arg = None

    def get_request_credentials(self):
        token = self.get_request_token()
        if token is None:
            return None

        return self.get_credentials_from_token(token)

    def get_request_token(self):
        authorization = flask.request.headers.get("Authorization")
        if authorization is not None:
            return self.get_token_from_authorization(authorization)

        if self.credentials_arg is not None:
            return flask.request.args.get(self.credentials_arg)

        return None

    def get_token_from_authorization(self, authorization):
        try:
            scheme, token = authorization.split()
        except (AttributeError, ValueError) as e:
            raise ApiError(401, {"code": "invalid_authorization"}) from e

        if scheme.lower() != self.header_scheme.lower():
            raise ApiError(401, {"code": "invalid_authorization.scheme"})

        return token

    def get_credentials_from_token(self, token):
        """Get the credentials from the token from the request.

        :param str token: The token from the request headers or query.
        :return: The credentials from the token.
        """
        raise NotImplementedError()


class HeaderAuthentication(HeaderAuthenticationBase):
    """Header authentication component where the token is the credential.

    This authentication component is useful for simple applications where the
    token itself is the credential, such as when it is a fixed secret shared
    between the client and the server that uniquely identifies the client.
    """

    def get_credentials_from_token(self, token):
        return token
