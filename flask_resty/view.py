import itertools

import flask
from flask.views import MethodView
from marshmallow import fields
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Load
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.exceptions import NotFound

from . import meta
from .authentication import NoOpAuthentication
from .authorization import NoOpAuthorization
from .decorators import request_cached_property
from .exceptions import ApiError
from .spec import ApiViewDeclaration, ModelViewDeclaration
from .utils import iter_validation_errors, settable_property

# -----------------------------------------------------------------------------


class ApiView(MethodView):
    """Extends :py:class:`flask.views.MethodView` and provides access control,
    input / output contracts and a uniform structure for rendering responses
    with RESTful semantics.

    ...
    """

    #: The :py:class:`marshmallow.Schema` for serialization and
    #: deserialization.
    schema = None
    #: The primary keys of this resource.
    id_fields = ('id',)
    #: The :py:class:`marshmallow.Schema` for deserializing
    #: the query params in the :py:data:`flask.Request.args`.
    args_schema = None

    #: The authentication scheme. See :py:class:`AuthenticationBase`.
    authentication = NoOpAuthentication()
    #: The authorization scheme. See :py:class:`AuthorizationBase`.
    authorization = NoOpAuthorization()

    #: An :py:class:`apispec.APISpec` for generating API documentation.
    spec_declaration = ApiViewDeclaration()

    def dispatch_request(self, *args, **kwargs):
        """Apply the authentication and authorization schemes before
        delegating the dispatch to Flask. Any provided `*args` or `*kwargs`
        will be passed to :py:meth:`flask.Flask.dispatch_request`.
        """
        self.authentication.authenticate_request()
        self.authorization.authorize_request()

        return super(ApiView, self).dispatch_request(*args, **kwargs)

    def serialize(self, item, **kwargs):
        """Serialize an item using the :py:attr:`serializer`. Any provided
        `**kwargs` will be passed to :py:meth:`marshmallow.Schema.dump`.

        :param object item: The object to serialize
        :return: The serialized object
        :rtype: dict
        """
        return self.serializer.dump(item, **kwargs).data

    @settable_property
    def serializer(self):
        """The :py:class:`marshmallow.Schema` for serialization. Overrides
        :py:attr:`ApiView.schema`.
        """
        return self.schema

    def make_items_response(self, items, *args):
        """Create an HTTP response by serializing the provided `items` into the
        response body.

        :param list items: The objects to serialize into the response body.
        :return: The HTTP response
        :rtype: :py:class:`flask.Response`
        """
        data_out = self.serialize(items, many=True)
        return self.make_response(data_out, *args, items=items)

    def make_item_response(self, item, *args):
        """Create an HTTP by serializing the provided item into the response
        body.

        :param object item: The object to serialize into the response body.
        :return: The HTTP response
        :rtype: :py:class:`flask.Response`
        """
        data_out = self.serialize(item)
        self.set_item_response_meta(item)
        return self.make_response(data_out, *args, item=item)

    def set_item_response_meta(self, item):
        pass

    def make_response(self, data, *args, **kwargs):
        """Create an HTTP response with the provided `data` in the response
        body along with any metadata from the Flask-RESTy context.

        :return: The HTTP response
        :rtype: :py:class:`flask.Response`
        """
        body = self.make_response_body(data, meta.get_response_meta())
        return self.make_raw_response(flask.jsonify(body), *args, **kwargs)

    def make_response_body(self, data, response_meta):
        """Prepare the response body. Stores the provided `data` in a field
        named `data`. If `response_meta` is provided it is stored in a field
        named `meta`.

        :return: The HTTP response body
        :rtype: dict
        """
        body = self.render_response_body(data, meta.get_response_meta())
        return self.make_raw_response(body, *args, **kwargs)

    def render_response_body(self, data, response_meta):
        body = {'data': data}
        if response_meta is not None:
            body['meta'] = response_meta

        return flask.jsonify(body)

    def make_raw_response(self, *args, **kwargs):
        """Create a :py:class:`flask.Response`. `args` are passed to
        :py:func:`flask.make_response`. `kwargs` are used to populate the
        response body.

        :return: The HTTP response
        :rtype: :py:class:`flask.Response`
        """
        response = flask.make_response(*args)
        for key, value in kwargs.items():
            setattr(response, key, value)
        return response

    def make_empty_response(self, **kwargs):
        """Create a :py:class:`flask.Response` with an empty body and a status
        code of 204.

        :return: The HTTP response
        :rtype: :py:class:`flask.Response`
        """
        return self.make_raw_response('', 204, **kwargs)

    def make_created_response(self, item):
        """Create an HTTP response for the created `item`. The response will
        have a status code of 201 and a ``Location`` header that references
        the API endpoint where the created `item` can be retrieved.

        :return: The HTTP response
        :rtype: :py:class:`flask.Response`
        """
        response = self.make_item_response(item, 201)
        location = self.get_location(item)
        if location is not None:
            response.headers['Location'] = location
        return response

    def get_location(self, item):
        """Create the URL that will reference the given `item`.

        :return: A URL
        :rtype: str
        """
        id_dict = {
            id_field: getattr(item, id_field) for id_field in self.id_fields
        }
        return flask.url_for(flask.request.endpoint, _method='GET', **id_dict)

    def get_request_data(self, **kwargs):
        """Retrieve the data provided under the ``data`` key in the request
        body.

        :return: The deserialized request data
        :rtype: object
        """
        data_raw = self.parse_request_data()
        return self.deserialize(data_raw, **kwargs)

    def parse_request_data(self):
        try:
            data_raw = flask.request.get_json()['data']
        except TypeError:
            raise ApiError(400, {'code': 'invalid_body'})
        except KeyError:
            raise ApiError(400, {'code': 'invalid_data.missing'})

        return data_raw

    def deserialize(self, data_raw, expected_id=None, **kwargs):
        """Use the :py:attr:`deserializer` to deserialize the data provided in
        `data_raw`. If `expected_id` is provided it is checked against the
        corresponding field in the deserialized data.

        :return: The deserialized data
        :rtype: object
        """
        data, errors = self.deserializer.load(data_raw, **kwargs)
        if errors:
            raise ApiError(422, *(
                self.format_validation_error(error)
                for error in iter_validation_errors(errors)
            ))

        self.validate_request_id(data, expected_id)
        return data

    @settable_property
    def deserializer(self):
        """The :py:class:`marshmallow.Schema` for deserialization. Overrides
        :py:attr:`ApiView.schema`.
        """
        return self.schema

    def format_validation_error(self, error):
        """Create a dictionary that describes the validation error provided in
        `error`. The response body has the following structure::

            code:
                type: string
                description: Always the literal `invalid_data`
            detail:
                type: string
                description: The message from the provided `error`
            source:
                type: object
                properties:
                    pointer:
                        type: string
                        description: An XPath to the field that caused the error

        :return: The formatted validation error
        :rtype: dict
        """
        message, path = error

        pointer = '/data/{}'.format(
            '/'.join(str(field_key) for field_key in path),
        )

        return {
            'code': 'invalid_data',
            'detail': message,
            'source': {'pointer': pointer},
        }

    def validate_request_id(self, data, expected_id):
        """Check that the `expected_id` has been provided on the
        corresponding field in `data`. If `expected_id` is False, all
        of the fields in :py:attr:`id_fields` are checked.

        :raises ApiError: If the necessary IDs are not present and correct
        """
        if expected_id is None:
            return

        if expected_id is False:
            for id_field in self.id_fields:
                if id_field in data:
                    raise ApiError(403, {'code': 'invalid_id.forbidden'})
            return

        try:
            id = self.get_data_id(data)
        except KeyError:
            raise ApiError(422, {'code': 'invalid_id.missing'})

        if id != expected_id:
            raise ApiError(409, {'code': 'invalid_id.mismatch'})

    def get_data_id(self, data):
        """Collect all of the values corresponding to the fields in
        :py:attr:`id_fields`.

        :return: One or more identifier values
        :rtype: tuple or str
        """
        if len(self.id_fields) == 1:
            return data[self.id_fields[0]]

        return tuple(data[id_field] for id_field in self.id_fields)

    @request_cached_property
    def request_args(self):
        """Use args_schema to parse request query arguments."""
        args = flask.request.args
        data_raw = {}

        for field_name, field in self.args_schema.fields.items():
            if field_name in args:
                args_key = field_name
            elif field.load_from and field.load_from in args:
                args_key = field.load_from
            else:
                continue

            value = args.getlist(args_key)
            if not self.is_list_field(field) and len(value) == 1:
                value = value[0]

            data_raw[field_name] = value

        return self.deserialize_args(data_raw)

    def is_list_field(self, field):
        """Predicate that indicates if the provided `field` is an instance
        of :py:class:`marshmallow.fields.List`.

        :return: True if the field is a List, False otherwise
        :rtype: bool
        """
        return isinstance(field, fields.List)

    def deserialize_args(self, data_raw, **kwargs):
        """Deserialize the data provided in `data_raw` using the
        :py:attr:`args_schema`.

        :return: The deserialized data
        :rtype: object
        """
        data, errors = self.args_schema.load(data_raw, **kwargs)
        if errors:
            raise ApiError(422, *(
                self.format_parameter_validation_error(message, parameter)
                for parameter, messages in errors.items()
                for message in messages
            ))

        return data

    def format_parameter_validation_error(self, message, parameter):
        """Create a dictionary that describes a parameter validation error. The
        response has the following structure::

            code:
                type: string
                description: Always the literal `invalid_parameter`
            detail:
                type: string
                description: The message from the provided `error`
            source:
                type: object
                properties:
                    parameter:
                        type: string
                        description: An XPath to the parameter that caused the error

        :return: The formatted parameter validation error
        :rtype: dict
        """
        return {
            'code': 'invalid_parameter',
            'detail': message,
            'source': {'parameter': parameter},
        }

    def get_id_dict(self, id):
        """Uses the sequence of ids provided in `id` to map the field names in
        :py:attr:`id_fields` to their corresponding values.

        :return: A mapping from id field names to id field values
        :rtype: dict
        """
        if len(self.id_fields) == 1:
            id = (id,)

        return dict(zip(self.id_fields, id))


class ModelView(ApiView):
    """Extends :py:class:`ApiView` and provides an interface to the ORM
    with additional abstractions for managing the composition and order of
    the data retrieved from the database.

    ...
    """
    #: A sqlalchemy model that inherits the declarative base class
    model = None

    #: An instance of :py:class:`filtering.Filtering`
    filtering = None
    #: An instance of :py:class:`sorting.SortingBase`
    sorting = None
    #: An instance of :py:class:`pagination.PaginationBase`
    pagination = None

    #: A :py:class:`related.Related` class for resolving related resources
    related = None

    #: An :py:class:`apispec.APISpec` for generating API documentation.
    spec_declaration = ModelViewDeclaration()

    @settable_property
    def session(self):
        return flask.current_app.extensions['sqlalchemy'].db.session

    @settable_property
    def query(self):
        """The SQLAlchemy query for the view.

        Override this to customize the query to fetch items in this view.

        By default, this applies the filter from the view's `authorization` and
        the query options from `base_query_options` and `query_options`.
        """
        query = self.model.query
        query = self.authorization.filter_query(query, self)
        query = query.options(
            *itertools.chain(self.base_query_options, self.query_options)
        )

        return query

    #: Base query options to apply before `query_options`.
    #:
    #: Set this on a base class to define base query options for its
    #: subclasses, while still allowing those subclasses to define their own
    #: additional query options via `query_options`.
    #:
    #: For example, set this to ``(raiseload('*', sql_only=True),)`` to prevent
    #: all implicit SQL-emitting relationship loading, and force all
    #: relationship loading to be explicitly defined via `query_options`.
    base_query_options = ()

    @settable_property
    def query_options(self):
        """Options to apply to the query for the view.

        Set this to configure relationship and column loading.

        By default, this calls the ``get_query_options`` method on the
        serializer with a `Load` object bound to the model, if that serializer
        method exists.

        :return: A sequence of query options
        :rtype: tuple
        """
        if not hasattr(self.serializer, 'get_query_options'):
            return ()

        return self.serializer.get_query_options(Load(self.model))

    def get_list(self):
        """Get a sequence of items using :py:attr:`model`. Applies pagination
        if set in :py:attr:`pagination`.

        :return: A sequence of items
        :rtype: list
        """
        return self.paginate_list_query(self.get_list_query())

    def get_list_query(self):
        """Get the query that retrieves a sequence of items. Applies
        filtering and sorting if set in :py:attr:`filtering` and
        :py:attr:`sorting` respectively.

        :return: The mutated query
        :rtype: :py:class:`sqlalchemy.orm.query.Query`
        """
        query = self.query
        query = self.filter_list_query(query)
        query = self.sort_list_query(query)
        return query

    def filter_list_query(self, query):
        """Applies filtering to the provided `query` if set in
        :py:attr:`filtering`.

        :param: A SQL query
        :type: :py:class:`sqlalchemy.orm.query.Query`
        :return: The filtered query
        :rtype: :py:class:`sqlalchemy.orm.query.Query`
        """
        if not self.filtering:
            return query

        return self.filtering.filter_query(query, self)

    def sort_list_query(self, query):
        """Applies sorting to the provided `query` if set in
        :py:attr:`sorting`.

        :param: A SQL query
        :type: :py:class:`sqlalchemy.orm.query.Query`
        :return: The sorted query
        :rtype: :py:class:`sqlalchemy.orm.query.Query`
        """
        if not self.sorting:
            return query

        return self.sorting.sort_query(query, self)

    def paginate_list_query(self, query):
        """Applies pagination to the provided `query` if set in
        :py:attr:`pagination`.

        :param: A SQL query
        :type: :py:class:`sqlalchemy.orm.query.Query`
        :return: The paginated query
        :rtype: :py:class:`sqlalchemy.orm.query.Query`
        """
        if not self.pagination:
            return query.all()

        return self.pagination.get_page(query, self)

    def get_item_or_404(self, id, **kwargs):
        """Similar to Django's :py:func:`django.shortcuts.get_object_or_404`.
        `kwargs` are passed to :py:meth:`get_item`.

        :param id: One or more primary keys
        :type: str or seq
        :return: An instance of the :py:attr:`model`
        :rtype: object
        """
        try:
            item = self.get_item(id, **kwargs)
        except NoResultFound:
            raise NotFound()

        return item

    def get_item(
        self,
        id,
        with_for_update=False,
        create_missing=False,
        will_update_item=False,
    ):
        """Get a single item by `id`.

        :param id: One or more primary keys
        :type: str or seq
        :param bool with_for_update: If True, a ``OR UPDATE`` clause will be
            appended. See :py:meth:`sqlalchemy.orm.query.Query.with_for_update`.
        :param bool create_missing: If True, the item will be created if it
            cannot be retrieved. 
        :param bool will_update_item: If True, no authorization will
            be applied before adding the item to the
            :py:class:`sqlalchemy.orm.Session`. Use this flag if you intend to
            call :py:meth:`update_item`.
        :return: An instance of the :py:attr:`model`
        :rtype: object
        """
        try:
            # Can't use self.query.get(), because query might be filtered.
            item_query = self.query.filter(*(
                getattr(self.model, field) == value
                for field, value in self.get_id_dict(id).items()
            ))
            if with_for_update:
                item_query = item_query.with_for_update(of=self.model)

            item = item_query.one()
        except NoResultFound as e:
            if not create_missing:
                raise

            try:
                item = self.create_missing_item(id)

                if will_update_item:
                    # Bypass authorizating the save if we are getting the item
                    # for update, as update_item will make that check.
                    self.session.add(item)
            except ApiError:
                # Raise the original not found error instead of the
                # authorization error.
                raise e

        return item

    def deserialize(self, data_raw, **kwargs):
        """Apply the :py:attr:`deserializer` to the provided data in
        `data_raw`. If any of the fields in the data are mapped in
        :py:attr:`related` they will be resolved to their corresponding
        values and included in the deserialized object. `kwargs` are
        passed to :py:meth:`ApiView.deserialize`.

        :param dict data_raw:
        :return: The deserialized object
        :rtype: object
        """
        data = super(ModelView, self).deserialize(data_raw, **kwargs)
        return self.resolve_related(data)

    def resolve_related(self, data):
        """Resolves any fields in `data` that have been mapped in
        :py:attr:`related`.

        :param object data: A deserialized object
        :return: The object with related fields resolved
        :rtype: object
        """
        if not self.related:
            return data

        return self.related.resolve_related(data)

    def resolve_related_item(self, data):
        """Resolves any fields in `data` that correspond to a a field in
        :py:attr:`id_fields`.

        :param object data: A deserialized object
        :return: The object with id fields resolved
        :rtype: object
        """
        try:
            id = self.get_data_id(data)
        except KeyError:
            raise ApiError(422, {'code': 'invalid_related.missing_id'})

        return self.resolve_related_id(id)

    def resolve_related_id(self, id):
        """Get an item that corresponds to the provided `id`.

        :param id: One or more primary keys
        :type: str or seq
        :return: An object
        :rtype: object
        """
        try:
            item = self.get_item(id)
        except NoResultFound:
            raise ApiError(422, {'code': 'invalid_related.not_found'})

        return item

    def create_missing_item(self, id):
        """Create an item that corresponds to the provided `id`.

        :param id: One or more primary keys
        :type: str or seq
        :return: An object
        :rtype: object
        """
        return self.create_item(self.get_id_dict(id))

    def create_item(self, data):
        """Create an item using the deserialized `data`. Applies the
        authorization scheme in :py:attr:`authorization`.

        :param dict data: The deserialized data
        :return: An instance of the :py:attr:`model`
        :rtype: object
        """
        item = self.model(**data)

        self.authorization.authorize_create_item(item)

        return item

    def add_item(self, item):
        """Add the provided `item` to the :py:class:`sqlalchemy.orm.Session`.
        Applies the authorization scheme in :py:attr:`authorization`.

        :param object item: An instance of the :py:attr:`model`
        """
        self.session.add(item)

        self.authorization.authorize_save_item(item)

    def create_and_add_item(self, data):
        """Create an item using the deserialized `data` and add it to the
        :py:class:`sqlalchemy.orm.Session`.

        :param dict data: The deserialized data
        :return: An instance of the :py:attr:`model`
        :rtype: object
        """
        item = self.create_item(data)
        self.add_item(item)
        return item

    def update_item(self, item, data):
        """Update the `item` using provided `data`. Applies the authorization
        scheme in :py:attr:`authorization`.

        :param object item: An instance of the :py:attr:`model`
        :param dict data: The update data
        """
        self.authorization.authorize_update_item(item, data)

        for key, value in data.items():
            setattr(item, key, value)

        self.authorization.authorize_save_item(item)

    def delete_item(self, item):
        """Delete the `item` from the :py:class:`sqlalchemy.orm.Session`.
        Applies the authorization scheme in :py:attr:`authorization`.

        :param object item: An instance of the :py:attr:`model`
        """
        self.authorization.authorize_delete_item(item)

        self.session.delete(item)

    def flush(self):
        """Calls :py:meth:`sqlalchemy.orm.Session.flush` handling any
        :py:class:`IntegrityError`.

        :raises: :py:class:`ApiError` if the flush results in an
            :py:class:`IntegrityError`.
        """
        try:
            # Flushing allows checking invariants without committing.
            self.session.flush()
        # Don't catch DataErrors here, as they arise from bugs in validation in
        # the schema.
        except IntegrityError as e:
            raise self.resolve_integrity_error(e)

    def commit(self):
        """Calls :py:meth:`sqlalchemy.orm.Session.commit` handling any
        :py:class:`IntegrityError`.

        :raises: :py:class:`ApiError` if the commit results in an
            :py:class:`IntegrityError`.
        """
        try:
            self.session.commit()
        # Don't catch DataErrors here, as they arise from bugs in validation in
        # the schema.
        except IntegrityError as e:
            raise self.resolve_integrity_error(e)

    def resolve_integrity_error(self, error):
        """Resolves the `error`. If the postgres error code corresponds to a
        ``not_null_violation`` or a ``check_violation`` the error is
        returned unmodified. Otherwise, a generic conflict :py:class:`ApiError`
        is returned.

        :return: The resolved error
        :rtype: :py:class:`Exception`
        """
        original_error = error.orig

        if (
            hasattr(original_error, 'pgcode') and
            original_error.pgcode in (
                '23502',  # not_null_violation
                '23514',  # check_violation
            )
        ):
            # Using the psycopg2 error code, we can tell that this was not from
            # an integrity error that was not a conflict. This means there was
            # a schema bug, so we emit an interal server error instead.
            return error

        flask.current_app.logger.exception("handled integrity error")
        return ApiError(409, {'code': 'invalid_data.conflict'})

    def set_item_response_meta(self, item):
        """Uses the `item` to set metadata on the Flask-RESTy context.

        :param object item: An object
        """
        super(ModelView, self).set_item_response_meta(item)
        self.set_item_response_meta_pagination(item)

    def set_item_response_meta_pagination(self, item):
        """If :py:attr:`pagination` is set, the `item` is used to set metadata
        from the pagination class on the Flask-RESTy context.

        :param object item: An object
        """
        if not self.pagination:
            return

        meta.update_response_meta(self.pagination.get_item_meta(item, self))


class GenericModelView(ModelView):
    """Extends :py:class:`ModelView` exposing a generic CRUD interface.

    ...
    """
    def list(self):
        """Composes :py:meth:`get_list` and :py:meth:`make_items_response` to
        fetch a list of items.

        :return: The HTTP response
        :rtype: :py:class:`flask.Response`
        """
        items = self.get_list()
        return self.make_items_response(items)

    def retrieve(self, id, create_missing=False):
        """Composes :py:meth:`get_item_or_404` and
        :py:meth:`make_item_response` to fetch a single item.

        :param id: One or more primary keys
        :type id: str or seq
        :param bool create_missing: Passed to :py:meth:`get_item_or_404`
        :return: The HTTP response
        :rtype: :py:class:`flask.Response`
        """
        item = self.get_item_or_404(id, create_missing=create_missing)
        return self.make_item_response(item)

    def create(self, allow_client_id=False):
        """Create a new item by composing :py:meth:`get_request_data`,
        :py:meth:`create_and_add_item` and :py:meth:`make_created_response`.

        :param allow_client_id: If True, the :py:attr:`id_fields` are
            permitted to be present in the request data.
        :type allow_client_id: bool
        :return: The HTTP response
        :rtype: :py:class:`flask.Response`
        """
        expected_id = None if allow_client_id else False
        data_in = self.get_request_data(expected_id=expected_id)

        item = self.create_and_add_item(data_in)
        self.commit()

        return self.make_created_response(item)

    def update(
        self,
        id,
        create_missing=False,
        partial=False,
        return_content=False,
    ):
        """Update an item by calling :py:meth:`update_item` on the item and
        update data, which are retrieved with :py:meth:`get_item_or_404` and
        :py:meth:`get_request_data` respectively.

        :param id: One or more primary keys
        :type id: str or seq
        :param create_missing: Passed to :py:meth:`get_item_or_404`
        :type create_missing: bool
        :param partial: Passed to :py:meth:`get_request_data`
        :type partial: bool
        :param return_content: If True, the updated item will be included in
            the response body.
        :type return_content: bool
        :return: The HTTP response
        :rtype: :py:class:`flask.Response`
        """
        # No need to authorize creating the missing item, as we will authorize
        # before saving to database below.
        item = self.get_item_or_404(
            id,
            create_missing=create_missing,
            will_update_item=True,
        )
        data_in = self.get_request_data(expected_id=id, partial=partial)

        self.update_item(item, data_in)
        self.commit()

        if return_content:
            return self.make_item_response(item)

        return self.make_empty_response(item=item)

    def destroy(self, id):
        """Composes :py:meth:`get_item_or_404` and :py:meth:`delete_item`
        to destroy a single item. An empty response is returned.

        :param id: One or more primary keys
        :type id: str or seq
        :return: The HTTP response
        :rtype: :py:class:`flask.Response`
        """
        item = self.get_item_or_404(id)

        self.delete_item(item)
        self.commit()

        return self.make_empty_response()
