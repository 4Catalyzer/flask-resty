from . import authentication
from .exceptions import ApiError

# -----------------------------------------------------------------------------


class AuthorizationBase:
    """Base class for the API authorization components.

    Authorization components control access to objects based on the credentials
    from authentication component.

    Authorization components can control access in the following ways:

    - Disallowing a request as a whole
    - Filtering the list of visible rows in the database
    - Disallowing specific modify actions

    For many CRUD endpoints, :py:class:`AuthorizeModifyMixin` allows consistent
    control of modify operations.
    """

    def get_request_credentials(self):
        """Retrieve the credentials stored in the
        :py:class:`flask.ctx.AppContext`.
        """
        return authentication.get_request_credentials()

    def authorize_request(self):
        """Authorization hook called before processing a request.

        Typically this hook will inspecting :py:data:`flask.request`.
        """
        raise NotImplementedError()

    def filter_query(self, query, view):
        """Filter a query to hide unauthorized rows.

        :param query: The SQL construction object.
        :type query: :py:class:`sqlalchemy.orm.query.Query`
        :param view: The View instance
        :type view: :py:class:`ModelView`
        :return: The filtered SQL construction object.
        :rtype: :py:class:`sqlalchemy.orm.query.Query`
        """
        raise NotImplementedError()

    def authorize_save_item(self, item):
        """Authorization hook called before saving a created or updated item.

        This will generally be called after `authorize_create_item` or
        `authorize_update_item` below.

        :param obj item: The model instance
        """
        raise NotImplementedError()

    def authorize_create_item(self, item):
        """Authorization hook called before creating a new item.

        :param obj item: The model instance
        """
        raise NotImplementedError()

    def authorize_update_item(self, item, data):
        """Authorization hook called before updating an existing item.

        :param obj item: The model instance
        :param dict data: A mapping from field names to updated values
        """
        raise NotImplementedError()

    def authorize_delete_item(self, item):
        """Authorization hook called before deleting an existing item.

        :param obj item: The model instance
        """
        raise NotImplementedError()


class HasCredentialsAuthorizationBase(AuthorizationBase):
    """A base authorization component that requires some authentication.

    This authorization component doesn't check the credentials, but will block
    all requests that do not provide some credentials.
    """

    def authorize_request(self):
        if self.get_request_credentials() is None:
            raise ApiError(401, {"code": "invalid_credentials.missing"})


# -----------------------------------------------------------------------------


class AuthorizeModifyMixin(AuthorizationBase):
    """An authorization component that consistently authorizes all modifies.

    Child classes should implement :py:meth:`authorize_modify_item`.
    """

    def authorize_save_item(self, item):
        self.authorize_modify_item(item, "save")

    def authorize_create_item(self, item):
        self.authorize_modify_item(item, "create")

    def authorize_update_item(self, item, data):
        self.authorize_modify_item(item, "update")

    def authorize_delete_item(self, item):
        self.authorize_modify_item(item, "delete")

    def authorize_modify_item(self, item, action):
        """Authorization hook for all modification actions on an item.

        :param obj item: The model instance
        :param str action: One of ``'save' | 'create' | 'update' | 'delete'``
        """
        raise NotImplementedError()


# -----------------------------------------------------------------------------


class NoOpAuthorization(AuthorizationBase):
    """An authorization component that allows any action."""

    def authorize_request(self):
        pass

    def filter_query(self, query, view):
        return query

    def authorize_save_item(self, item):
        pass

    def authorize_create_item(self, item):
        pass

    def authorize_update_item(self, item, data):
        pass

    def authorize_delete_item(self, item):
        pass


class HasAnyCredentialsAuthorization(
    HasCredentialsAuthorizationBase, NoOpAuthorization
):
    """An authorization component that allows any action when authenticated.

    This doesn't check the credentials; it just checks that some valid
    credentials were provided.
    """

    pass
