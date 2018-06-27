from . import context

# -----------------------------------------------------------------------------


def get_request_credentials():
    return context.get('request_credentials')


def set_request_credentials(credentials):
    context.set('request_credentials', credentials)


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
