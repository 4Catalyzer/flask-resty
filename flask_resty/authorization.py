from . import authentication
from .exceptions import ApiError

# -----------------------------------------------------------------------------


class AuthorizationBase(object):
    def get_request_credentials(self):
        return authentication.get_request_credentials()

    def authorize_request(self):
        raise NotImplementedError()

    def filter_query(self, query, view):
        raise NotImplementedError()

    def authorize_save_item(self, item):
        raise NotImplementedError()

    def authorize_update_item(self, item, data):
        raise NotImplementedError()

    def authorize_delete_item(self, item):
        raise NotImplementedError()


# -----------------------------------------------------------------------------


class NoOpAuthorization(object):
    def authorize_request(self):
        pass

    def filter_query(self, query, view):
        return query

    def authorize_save_item(self, item):
        pass

    def authorize_update_item(self, item, data):
        pass

    def authorize_delete_item(self, item):
        pass


# -----------------------------------------------------------------------------


class HasCredentialsAuthorizationBase(AuthorizationBase):
    def authorize_request(self):
        if self.get_request_credentials() is None:
            raise ApiError(401, {'code': 'invalid_credentials.missing'})


class HasAnyCredentialsAuthorization(
    HasCredentialsAuthorizationBase, NoOpAuthorization, AuthorizationBase,
):
    pass
