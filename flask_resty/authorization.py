from . import authentication
from .exceptions import ApiError

# -----------------------------------------------------------------------------


class AuthorizationBase(object):
    """Base class for the API authorization scheme. Typically you will want
    to use the :py:class:`AuthorizeModifyMixin` to implement uniform
    authorization logic for each CRUD operation.

    Implementing classes can customize the authorization scheme at multiple
    points in an :py:class:`ApiView`:

    * When requests are processed
    * When ORM operations are called
    * When queries are executed
    """
    def get_request_credentials(self):
        """Retrieves the credentials stored in the
        :py:class:`flask.ctx.AppContext`.
        """
        return authentication.get_request_credentials()

    def authorize_request(self):
        """Authorize the current request. Typically this is done by inspecting
        :py:data:`flask.request`.
        """
        raise NotImplementedError()

    def filter_query(self, query, view):
        """Apply a filter to the provided `query` using the model, schema or
        other data from the provided `view`.

        :param query: The SQL construction object.
        :type query: :py:class:`sqlalchemy.orm.query.Query`
        :param view: The View instance
        :type view: :py:class:`ApiView`
        :return: The filtered SQL construction object.
        :rtype: :py:class:`sqlalchemy.orm.query.Query`
        """
        raise NotImplementedError()

    def authorize_save_item(self, item):
        """Authorize attempts to add a model instance to the current
        :py:class:`sqlalchemy.orm.session.Session` or update a model instance
        from the current :py:class:`sqlalchemy.orm.session.Session`.

        :param obj item: The model instance
        """
        raise NotImplementedError()

    def authorize_create_item(self, item):
        """Authorize attempts to create a new instance of a model that
        inherits from the declarative base class.

        :param obj item: The model instance
        """
        raise NotImplementedError()

    def authorize_update_item(self, item, data):
        """Authorize attempts to update an existing instance of a model that
        inherits from the declarative base class.

        :param obj item: The model instance
        :param dict data: A mapping from field names to updated values
        """
        raise NotImplementedError()

    def authorize_delete_item(self, item):
        """Authorize attempts to delete an existing instance of a model that
        inherits from the declarative base class.

        :param obj item: The model instance
        """
        raise NotImplementedError()


class HasCredentialsAuthorizationBase(AuthorizationBase):
    """An authorization scheme where only authenticated requests are allowed.
    """
    def authorize_request(self):
        if self.get_request_credentials() is None:
            raise ApiError(401, {'code': 'invalid_credentials.missing'})


# -----------------------------------------------------------------------------


class AuthorizeModifyMixin(AuthorizationBase):
    """An authorization scheme where each CRUD operation has uniform
    authorization logic.

    Implementing classes must implement :py:meth:`authorize_modify_item`.
    """
    def authorize_save_item(self, item):
        self.authorize_modify_item(item, 'save')

    def authorize_create_item(self, item):
        self.authorize_modify_item(item, 'create')

    def authorize_update_item(self, item, data):
        self.authorize_modify_item(item, 'update')

    def authorize_delete_item(self, item):
        self.authorize_modify_item(item, 'delete')

    def authorize_modify_item(self, item, action):
        """Authorize modification of the provided `item` based on the provided
        `action`.

        :param obj item: The model instance
        :param str action: One of ``'save' | 'create' | 'update' | 'delete'``
        """
        raise NotImplementedError()


# -----------------------------------------------------------------------------


class NoOpAuthorization(AuthorizationBase):
    """An authorization scheme that allows any request, passes through any query
    and accepts any ORM operation.
    """
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
    HasCredentialsAuthorizationBase, NoOpAuthorization,
):
    """The same as :py:class:`NoOpAuthorization` but only allows authenticated
    requests.
    """
    pass
