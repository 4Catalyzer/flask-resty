import flask

# -----------------------------------------------------------------------------


def get_request_credentials():
    return getattr(flask.g, 'jsonapiview_request_credentials', None)


def set_request_credentials(credentials):
    flask.g.jsonapiview_request_credentials = credentials


# -----------------------------------------------------------------------------


class AuthenticationBase(object):
    def authenticate_request(self):
        set_request_credentials(self.get_request_credentials())

    def get_request_credentials(self):
        raise NotImplementedError()
