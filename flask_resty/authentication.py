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
    implementation using JSON Web Tokens but you can use any authentication
    scheme by extending AuthenticationBase and implementing
    get_request_credentials.
    """
    def authenticate_request(self):
        """Stores the request credentials in the Flask AppContext. No
        validation is performed by Flask-RESTy. It is up to the implementor
        to validate the request in get_request_credentials.
        """
        set_request_credentials(self.get_request_credentials())

    def get_request_credentials(self):
        """Retrieve the credentials from the current request. Typically this
        is done by inspecting flask.request.

        Implementing classes should raise a 401 Unauthorized ApiError on
        authentication failure.
        """
        raise NotImplementedError()


# -----------------------------------------------------------------------------


class NoOpAuthentication(object):
    """An authentication scheme that always allows the request.
    """
    def authenticate_request(self):
        pass
