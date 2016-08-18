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
    def authenticate_request(self):
        set_request_credentials(self.get_request_credentials())

    def get_request_credentials(self):
        raise NotImplementedError()


# -----------------------------------------------------------------------------


class NoOpAuthentication(object):
    def authenticate_request(self):
        pass
