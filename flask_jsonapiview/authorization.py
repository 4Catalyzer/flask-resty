import flask
import logging

from . import authentication

# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------


class AuthorizationBase(object):
    def get_request_credentials(self):
        return authentication.get_request_credentials()

    def authorize_request(self):
        raise NotImplementedError()

    def filter_query(self, query):
        raise NotImplementedError()

    def authorize_save_item(self, item):
        raise NotImplementedError()

    def authorize_update_item(self, item, data):
        raise NotImplementedError()

    def authorize_delete_item(self, item):
        raise NotImplementedError()


# -----------------------------------------------------------------------------


class HasAnyCredentialsAuthorization(AuthorizationBase):
    def authorize_request(self):
        if self.get_request_credentials() is None:
            logger.warning("no request credentials")
            flask.abort(401)

    def filter_query(self, query):
        return query

    def authorize_save_item(self, item):
        pass

    def authorize_update_item(self, item, data):
        pass

    def authorize_delete_item(self, item):
        pass
