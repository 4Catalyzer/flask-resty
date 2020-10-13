import flask
import itertools
from flask.views import MethodView
from marshmallow import ValidationError, fields
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Load
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.exceptions import NotFound

from . import meta
from .authentication import NoOpAuthentication
from .authorization import NoOpAuthorization
from .decorators import request_cached_property
from .exceptions import ApiError
from .fields import DelimitedList
from .utils import settable_property

# -----------------------------------------------------------------------------


class ApiView(MethodView):
    """Base class for views that expose API endpoints.

    `ApiView` extends :py:class:`flask.views.MethodView` exposes functionality
    to deserialize request bodies and serialize response bodies according to
    standard API semantics.
    """

    #: The :py:class:`marshmallow.Schema` for serialization and
    #: deserialization.
    schema = None
    #: The identifying fields for the model.
    id_fields = ("id",)
    #: The :py:class:`marshmallow.Schema` for deserializing the query params in
    #: the :py:data:`flask.Request.args`.
    args_schema = None

    #: The authentication component. See :py:class:`AuthenticationBase`.
    authentication = NoOpAuthentication()
    #: The authorization component. See :py:class:`AuthorizationBase`.
    authorization = NoOpAuthorization()

    def dispatch_request(self, *args, **kwargs):
        """Handle an incoming request.

        By default, this checks request-level authentication and authorization
        before calling the upstream request handler.
        """
        self.authentication.authenticate_request()
        self.authorization.authorize_request()

        return super().dispatch_request(*args, **kwargs)

    def serialize(self, item, **kwargs):
        """Dump an item using the :py:attr:`serializer`.

        This doesn't technically serialize the item; it instead uses
        marshmallow to dump the item into a native Python data type. The actual
        serialization is done in `make_response`.

        Any provided `**kwargs` will be passed to
        :py:meth:`marshmallow.Schema.dump`.

        :param object item: The object to serialize
        :return: The serialized object
        :rtype: dict
        """
        return self.serializer.dump(item, **kwargs)

    @settable_property
    def serializer(self):
        """The :py:class:`marshmallow.Schema` for serialization.

        By default, this is :py:attr:`ApiView.schema`. This can be overridden
        to use a different schema for serialization.
        """
        return self.schema

    def make_items_response(self, items, *args):
        """Build a response for a sequence of multiple items.

        This serializes the items, then builds an response with the list of
        serialized items as its data.

        This is useful when returning a list of items.

        The response will have the items available as the ``items`` attribute.

        :param list items: The objects to serialize into the response body.
        :return: The HTTP response
        :rtype: :py:class:`flask.Response`
        """
        data_out = self.serialize(items, many=True)
        return self.make_response(data_out, *args, items=items)

    def make_item_response(self, item, *args):
        """Build a response for a single item.

        This serializes the item, then builds an response with the serialized
        item as its data. If the response status code is 201, then it will also
        include a ``Location`` header with the canonical URL of the item, if
        available.

        The response will have the item available as the ``item`` attribute.

        :param object item: The object to serialize into the response body.
        :return: The HTTP response
        :rtype: :py:class:`flask.Response`
        """
        data_out = self.serialize(item)
        self.set_item_response_meta(item)
        response = self.make_response(data_out, *args, item=item)

        if response.status_code == 201:
            location = self.get_location(item)
            if location is not None:
                response.headers["Location"] = location

        return response

    def set_item_response_meta(self, item):
        """Hook for setting additional metadata for an item.

        This should call `meta.update_response_meta` to set any metadata values
        to add to the response.

        :param object item: The object for which to generate metadata.
        :return:
        """
        pass

    def make_response(self, data, *args, **kwargs):
        """Build a response for arbitrary dumped data.

        This builds the response body given the data and any metadata from the
        request context. It then serializes the response.

        :return: The HTTP response
        :rtype: :py:class:`flask.Response`
        """
        body = self.render_response_body(data, meta.get_response_meta())
        return self.make_raw_response(body, *args, **kwargs)

    def render_response_body(self, data, response_meta):
        """Render the response data and metadata into a body.

        This is the final step of building the response payload before
        serialization.

        By default, this builds a dictionary with a ``data`` item for the
        response data and a ``meta`` item for the response metadata, if any.
        """
        body = {"data": data}
        if response_meta is not None:
            body["meta"] = response_meta

        return flask.jsonify(body)

    def make_raw_response(self, *args, **kwargs):
        """Convenience method for creating a :py:class:`flask.Response`.

        Any supplied keyword arguments are defined as attributes on the
        response object itself.

        :return: The HTTP response
        :rtype: :py:class:`flask.Response`
        """
        response = flask.make_response(*args)
        for key, value in kwargs.items():
            setattr(response, key, value)
        return response

    def make_empty_response(self, **kwargs):
        """Build an empty response.

        This response has a status code of 204 and an empty body.

        :return: The HTTP response
        :rtype: :py:class:`flask.Response`
        """
        return self.make_raw_response("", 204, **kwargs)

    def make_created_response(self, item):
        """Build a response for a newly created item.

        This response will be for the item data and will have a status code of
        201. It will include a ``Location`` header with the canonical URL of
        the created item, if available.

        :param object item: The created item.
        :return: The HTTP response
        :rtype: :py:class:`flask.Response`
        """
        return self.make_item_response(item, 201)

    def make_deleted_response(self, item):
        """Build a response for a deleted item.

        By default, this will be an empty response. The empty response will
        have the ``item`` attribute as with an item response.

        :param object item: The deleted item.
        :return: The HTTP response
        :rtype: :py:class:`flask.Response`
        """
        return self.make_empty_response(item=item)

    def get_location(self, item):
        """Get the canonical URL for an item.

        Override this to return ``None`` if no such URL is available.

        :param object item: The item.
        :return: The canonical URL for `item`.
        :rtype: str
        """
        id_dict = {
            id_field: getattr(item, id_field) for id_field in self.id_fields
        }
        return flask.url_for(flask.request.endpoint, _method="GET", **id_dict)

    def get_request_data(self, **kwargs):
        """Deserialize and load data from the body of the current request.

        By default, this will look for the value under the ``data`` key in a
        JSON request body.

        :return: The deserialized request data
        :rtype: dict
        """
        data_raw = self.parse_request_data()
        return self.deserialize(data_raw, **kwargs)

    def parse_request_data(self):
        """Deserialize the data for the current request.

        This will deserialize the request data from the request body into a
        native Python object that can be loaded by marshmallow.

        :return: The deserialized request data.
        """
        try:
            data_raw = flask.request.get_json()["data"]
        except TypeError as e:
            raise ApiError(400, {"code": "invalid_body"}) from e
        except KeyError as e:
            raise ApiError(400, {"code": "invalid_data.missing"}) from e

        return data_raw

    def deserialize(self, data_raw, *, expected_id=None, **kwargs):
        """Load data using the :py:attr:`deserializer`.

        This doesn't technically deserialize the data; it instead uses
        marshmallow to load and validate the data. The actual deserialization
        happens in `parse_request_data`.

        Any provided `**kwargs` will be passed to
        :py:meth:`marshmallow.Schema.load`.

        :param data_raw: The request data to load.
        :param expected_id: The expected ID in the request data. See
            `validate_request_id`.
        :return: The deserialized data
        :rtype: dict
        """
        try:
            data = self.deserializer.load(data_raw, **kwargs)
        except ValidationError as e:
            raise ApiError.from_validation_error(
                422, e, self.format_validation_error
            ) from e

        self.validate_request_id(data, expected_id)
        return data

    @settable_property
    def deserializer(self):
        """The :py:class:`marshmallow.Schema` for serialization.

        By default, this is :py:attr:`ApiView.schema`. This can be overridden
        to use a different schema for deserialization.
        """
        return self.schema

    def format_validation_error(self, message, path):
        """Convert marshmallow validation error data to a serializable form.

        This converts marshmallow validation error data to a standard
        serializable representation. By default, it converts errors into a
        dictionary of the form::

            {
                "code": "invalid_data",
                "detail": "<error message>",
                "source": {
                    "pointer": "/data/<field name>"
                }
            }

        :param str message: The marshmallow validation error message.
        :param tuple path: The path to the invalid field.
        :return: The formatted validation error.
        :rtype: dict
        """
        pointer = "/data/{}".format(
            "/".join(str(field_key) for field_key in path)
        )

        return {
            "code": "invalid_data",
            "detail": message,
            "source": {"pointer": pointer},
        }

    def validate_request_id(self, data, expected_id):
        """Check that the request data has the expected ID.

        This is generally used to assert that update operations include the
        correct item ID and that create operations do not include an ID.

        This works in one of three modes::
        - If `expected_id` is ``None``, do no checking
        - If `expected_id` is ``False``, check that no ID is provided
        - Otherwise, check that `data` has the expected ID

        :param data: The request data.
        :param expected_id: The ID or ID tuple, or False, or None.
        :raises ApiError: If the necessary IDs are not present and correct
        """
        if expected_id is None:
            return

        if expected_id is False:
            for id_field in self.id_fields:
                if id_field in data:
                    raise ApiError(403, {"code": "invalid_id.forbidden"})
            return

        try:
            id = self.get_data_id(data)
        except KeyError as e:
            raise ApiError(422, {"code": "invalid_id.missing"}) from e

        if id != expected_id:
            raise ApiError(409, {"code": "invalid_id.mismatch"})

    def get_data_id(self, data):
        """Get the ID as a scalar or tuple from request data.

        The ID will be a scalar if :py:attr:`id_fields` contains a single
        field or a tuple if it contains multiple.

        :return: The ID scalar or tuple.
        """
        if len(self.id_fields) == 1:
            return data[self.id_fields[0]]

        return tuple(data[id_field] for id_field in self.id_fields)

    @request_cached_property
    def request_args(self):
        """The query arguments for the current request.

        This uses :py:attr:`args_schema` to load the current query args. This
        value is cached per request, and will be computed the first time it is
        called for any request.

        :return: The query arguments.
        :rtype: dict
        """
        args = flask.request.args
        data_raw = {}

        for field_name, field in self.args_schema.fields.items():
            alternate_field_name = field.data_key

            if alternate_field_name and alternate_field_name in args:
                field_name = alternate_field_name
            elif field_name not in args:
                # getlist will return an empty list instead of raising a
                # KeyError for args that aren't present.
                continue

            if isinstance(field, fields.List) and not isinstance(
                field, DelimitedList
            ):
                value = args.getlist(field_name)
            else:
                value = args.get(field_name)

            data_raw[field_name] = value

        return self.deserialize_args(data_raw)

    def deserialize_args(self, data_raw, **kwargs):
        """Load parsed query arg data using :py:attr:`args_schema`.

        As with `deserialize`, contra the name, this handles loading with a
        schema rather than deserialization per se.

        :param dict data_raw: The raw query data.
        :param dict kwargs: Additional keyword arguments for `marshmallow.Schema.load`.
        :return: The deserialized data
        :rtype: object
        """
        try:
            data = self.args_schema.load(data_raw, **kwargs)
        except ValidationError as e:
            raise ApiError(
                422,
                *(
                    self.format_parameter_validation_error(message, parameter)
                    for parameter, messages in e.messages.items()
                    for message in messages
                ),
            ) from e

        return data

    def format_parameter_validation_error(self, message, parameter):
        """Convert a parameter validation error to a serializable form.

        This closely follows `format_validation_error`, but produces error
        dictionaries of the form::

            {
                "code": "invalid_parameter",
                "detail": "<error message>",
                "source": {
                    "parameter": "<parameter name>"
                }
            }

        :param str message: The validation error message.
        :param str parameter: The query parameter name.
        :return: The formatted parameter validation error
        :rtype: dict
        """
        return {
            "code": "invalid_parameter",
            "detail": message,
            "source": {"parameter": parameter},
        }

    def get_id_dict(self, id):
        """Convert an ID from `get_data_id` to dictionary form.

        This converts an ID from `get_data_id` into a dictionary where each ID
        value is keyed by the corresponding ID field name.

        :param id: An ID from `get_id_dict`
        :type: str or tuple
        :return: A mapping from ID field names to ID field values
        :rtype: dict
        """
        if len(self.id_fields) == 1:
            id = (id,)

        return dict(zip(self.id_fields, id))


class ModelView(ApiView):
    """Base class for API views tied to SQLAlchemy models.

    `ModelView` implements additional methods on top of those provided by
    `ApiView` to interact with SQLAlchemy models.

    The functionality in this class largely ties together the authorization and
    the model. It provides for access to the model query as appropriately
    filtered for authorized rows, and provides methods to create or update
    model instances from request data with authorization checks.

    It also provides functionality to apply filtering, sorting, and pagination
    when getting lists of items, and for resolving related items when
    deserializing request data.
    """

    #: A declarative SQLAlchemy model.
    model = None

    #: An instance of :py:class:`filtering.Filtering`.
    filtering = None
    #: An instance of :py:class:`sorting.SortingBase`.
    sorting = None
    #: An instance of :py:class:`pagination.PaginationBase`.
    pagination = None

    #: An instance of :py:class:`related.Related`.
    related = None

    @settable_property
    def session(self):
        """Convenience property for the current SQLAlchemy session."""
        return flask.current_app.extensions["sqlalchemy"].db.session

    @settable_property
    def query_raw(self):
        """The raw SQLAlchemy query for the view.

        This is the base query, without authorization filters or query options.
        By default, this is the query property on the model class. This can be
        overridden to remove filters attached to that query.
        """
        return self.model.query

    @settable_property
    def query(self):
        """The SQLAlchemy query for the view.

        Override this to customize the query to fetch items in this view.

        By default, this applies the filter from the view's `authorization` and
        the query options from `base_query_options` and `query_options`.
        """
        query = self.query_raw
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

        :return: A sequence of query options.
        :rtype: tuple
        """
        if not hasattr(self.serializer, "get_query_options"):
            return ()

        return self.serializer.get_query_options(Load(self.model))

    def get_list(self):
        """Retrieve a list of items.

        This takes the output of `get_list_query` and applies pagination.

        :return: The list of items.
        :rtype: list
        """
        return self.paginate_list_query(self.get_list_query())

    def get_list_query(self):
        """Build the query to retrieve a filtered and sorted list of items.

        :return: The list query.
        :rtype: :py:class:`sqlalchemy.orm.query.Query`
        """
        query = self.query
        query = self.filter_list_query(query)
        query = self.sort_list_query(query)
        return query

    def filter_list_query(self, query):
        """Apply filtering as specified to the provided `query`.

        :param: A SQL query
        :type: :py:class:`sqlalchemy.orm.query.Query`
        :return: The filtered query
        :rtype: :py:class:`sqlalchemy.orm.query.Query`
        """
        if not self.filtering:
            return query

        return self.filtering.filter_query(query, self)

    def sort_list_query(self, query):
        """Apply sorting as specified to the provided `query`.

        :param: A SQL query
        :type: :py:class:`sqlalchemy.orm.query.Query`
        :return: The sorted query
        :rtype: :py:class:`sqlalchemy.orm.query.Query`
        """
        if not self.sorting:
            return query

        return self.sorting.sort_query(query, self)

    def paginate_list_query(self, query):
        """Retrieve the requested page from `query`.

        If :py:attr:`pagination` is configured, this will retrieve the page as
        specified by the request and the pagination configuration. Otherwise,
        this will retrieve all items from the query.

        :param: A SQL query
        :type: :py:class:`sqlalchemy.orm.query.Query`
        :return: The paginated query
        :rtype: :py:class:`sqlalchemy.orm.query.Query`
        """
        if not self.pagination:
            return query.all()

        return self.pagination.get_page(query, self)

    def get_item_or_404(self, id, **kwargs):
        """Get an item by ID; raise a 404 if it not found.

        This will get an item by ID per `get_item` below. If no item is found,
        it will rethrow the `NoResultFound` exception as an HTTP 404.

        :param id: The item ID.
        :return: The item corresponding to the ID.
        :rtype: object
        """
        try:
            item = self.get_item(id, **kwargs)
        except NoResultFound as e:
            raise NotFound() from e

        return item

    def get_item(
        self,
        id,
        *,
        with_for_update=False,
        create_transient_stub=False,
    ):
        """Get an item by ID.

        The ID should be the scalar ID value if `id_fields` specifies a single
        field. Otherwise, it should be a tuple of each ID field value,
        corresponding to the elements of `id_fields`.

        :param id: The item ID.
        :param bool with_for_update: If set, lock the item row for updating
            using ``FOR UPDATE``.
        :param bool create_transient_stub: If set, create and return a
            transient stub for the item using `create_stub_item` if it is not
            found. This will not save the stub to the database.
        :return: The item corresponding to the ID.
        :rtype: object
        """
        try:
            # Can't use self.query.get(), because query might be filtered.
            item_query = self.query.filter(
                *(
                    getattr(self.model, field) == value
                    for field, value in self.get_id_dict(id).items()
                )
            )
            if with_for_update:
                item_query = item_query.with_for_update(of=self.model)

            item = item_query.one()
        except NoResultFound as e:
            if not create_transient_stub:
                raise

            try:
                item = self.create_stub_item(id)
            except ApiError:
                # Raise the original not found error instead of the
                # authorization error.
                raise e

        return item

    def deserialize(self, data_raw, **kwargs):
        """Load data using the :py:attr:`deserializer`.

        In addition to the functionality of :py:meth:`ApiView.deserialize`,
        this will resolve related items using the configured `related`.
        """
        data = super().deserialize(data_raw, **kwargs)
        return self.resolve_related(data)

    def resolve_related(self, data):
        """Resolve all related fields per :py:attr:`related`.

        :param object data: A deserialized object
        :return: The object with related fields resolved
        :rtype: object
        """
        if not self.related:
            return data

        return self.related.resolve_related(data)

    def resolve_related_item(self, data, **kwargs):
        """Retrieve the related item corresponding to the provided data stub.

        This is used by `Related` when this view is set for a field.

        :param dict data: Stub item data with ID fields.
        :return: The item corresponding to the ID in the data.
        :rtype: object
        """
        try:
            id = self.get_data_id(data)
        except KeyError as e:
            raise ApiError(422, {"code": "invalid_related.missing_id"}) from e

        return self.resolve_related_id(id, **kwargs)

    def resolve_related_id(self, id, **kwargs):
        """Retrieve the related item corresponding to the provided ID.

        This is used by `Related` when a field is specified as a `RelatedId`.

        :param id: The item ID.
        :return: The item corresponding to the ID.
        :rtype: object
        """
        try:
            item = self.get_item(id, **kwargs)
        except NoResultFound as e:
            raise ApiError(422, {"code": "invalid_related.not_found"}) from e

        return item

    def create_stub_item(self, id):
        """Create a stub item that corresponds to the provided ID.

        This is used by `get_item` when `create_transient_stub` is set.

        Override this to configure the creation of stub items.

        :param id: The item ID.
        :return: A transient stub item corresponding to the ID.
        :rtype: object
        """
        return self.create_item(self.get_id_dict(id))

    def create_item(self, data):
        """Create an item using the provided data.

        This will invoke `authorize_create_item` on the created item.

        Override this to configure the creation of items, e.g. by adding
        additional entries to `data`.

        :param dict data: The deserialized data.
        :return: The newly created item.
        :rtype: object
        """
        item = self.create_item_raw(data)
        self.authorization.authorize_create_item(item)
        return item

    def create_item_raw(self, data):
        """As with `create_item`, but without the authorization check.

        This is used by `create_item`, which then applies the authorization
        check.

        Override this instead of `create_item` when applying other
        modifications to the item that should take place before running the
        authorization check.

        :param dict data: The deserialized data.
        :return: The newly created item.
        :rtype: object
        """
        return self.model(**data)

    def add_item(self, item):
        """Add an item to the current session.

        This will invoke `authorize_save_item` on the item to add.

        :param object item: The item to add.
        """
        self.add_item_raw(item)
        self.authorization.authorize_save_item(item)

    def add_item_raw(self, item):
        """As with `add_item`, but without the authorization check.

        This is used by `add_item`, which then applies the authorization check.

        :param object item: The item to add.
        """
        self.session.add(item)

    def create_and_add_item(self, data):
        """Create an item using the provided data, then add it to the session.

        This uses `create_item` and `add_item`. Correspondingly, it will invoke
        both `authorize_create_item` and `authorize_save_item` on the item.

        :param dict data: The deserialized data.
        :return: The created and added item.
        :rtype: object
        """
        item = self.create_item(data)
        self.add_item(item)
        return item

    def update_item(self, item, data):
        """Update an existing item with the provided data.

        This will invoke `authorize_update_item` using the provided item and
        data before updating the item, then `authorize_save_item` on the
        updated item afterward.

        Override this to configure the updating of items, e.g. by adding
        additional entries to `data`.

        :param object item: The item to update.
        :param dict data: The deserialized data.
        :return: The newly updated item.
        :rtype: object
        """
        self.authorization.authorize_update_item(item, data)
        item = self.update_item_raw(item, data) or item
        self.authorization.authorize_save_item(item)
        return item

    def update_item_raw(self, item, data):
        """As with `update_item`, but without the authorization checks.

        Override this instead of `update_item` when applying other
        modifications to the item that should take place before and after the
        authorization checks in the above.

        :param object item: The item to update.
        :param dict data: The deserialized data.
        :return: The newly updated item.
        :rtype: object
        """
        for key, value in data.items():
            setattr(item, key, value)

    def delete_item(self, item):
        """Delete an existing item.

        This will run `authorize_delete_item` on the item before deleting it.

        :param object item: The item to delete.
        :return: The deleted item.
        :rtype: object
        """
        self.authorization.authorize_delete_item(item)
        item = self.delete_item_raw(item) or item
        return item

    def delete_item_raw(self, item):
        """As with `delete_item`, but without the authorization check.

        Override this to customize the delete behavior, e.g. by replacing the
        delete action with an update to mark the item deleted.

        :param object item: The item to delete.
        """
        self.session.delete(item)

    def flush(self, *, objects=None):
        """Flush pending changes to the database.

        This will check database level invariants, and will throw exceptions as
        with `commit` if any invariant violations are found.

        It's a common pattern to call `flush`, then make external API calls,
        then call `commit`. The `flush` call will do a preliminary check on
        database-level invariants, making it less likely that the `commit`
        operation will fail, and reducing the risk of the external systems
        being left in an inconsistent state.

        :param objects: If specified, the specific objects to flush. Otherwise,
            all pending changes will be flushed.
        :return:
        """
        try:
            # Flushing allows checking invariants without committing.
            self.session.flush(objects=objects)
        # Don't catch DataErrors here, as they arise from bugs in validation in
        # the schema.
        except IntegrityError as e:
            raise self.resolve_integrity_error(e) from e

    def commit(self):
        """Commit changes to the database.

        Any integrity errors that arise will be passed to
        `resolve_integrity_error`, which is expected to convert integrity
        errors corresponding to cross-row database-level invariant violations
        to HTTP 409 responses.

        :raises: :py:class:`ApiError` if the commit fails with integrity errors
            arising from foreign key or unique constraint violations.
        """
        try:
            self.session.commit()
        # Don't catch DataErrors here, as they arise from bugs in validation in
        # the schema.
        except IntegrityError as e:
            raise self.resolve_integrity_error(e) from e

    def resolve_integrity_error(self, error):
        """Convert integrity errors to HTTP error responses as appropriate.

        Certain kinds of database integrity errors cannot easily be caught by
        schema validation. These errors include violations of unique
        constraints and of foreign key constraints. While it's sometimes
        possible to check for those in application code, it's often best to let
        the database handle those. This will then convert those integrity
        errors to HTTP 409 responses.

        On PostgreSQL, this uses additional integrity error details to not
        convert NOT NULL violations and CHECK constraint violations to HTTP 409
        responses, as such checks should be done in the schema.

        :return: The resolved error.
        :rtype: :py:class:`Exception`
        """
        original_error = error.orig

        if hasattr(original_error, "pgcode") and original_error.pgcode in (
            "23502",  # not_null_violation
        ):
            # Using the psycopg2 error code, we can tell that this was not from
            # an integrity error that was not a conflict. This means there was
            # a schema bug, so we emit an interal server error instead.
            return error

        flask.current_app.logger.warning(
            "handled integrity error", exc_info=error
        )
        return ApiError(409, {"code": "invalid_data.conflict"})

    def set_item_response_meta(self, item):
        """Set the appropriate response metadata for the response item.

        By default, this adds the item metadata from the pagination component.

        :param object item: The item in the response.
        """
        super().set_item_response_meta(item)
        self.set_item_response_meta_pagination(item)

    def set_item_response_meta_pagination(self, item):
        """Set pagination metadata for the response item.

        This uses the configured pagination component to set pagination
        metadata for the response item.

        :param object item: The item in the response.
        """
        if not self.pagination:
            return

        meta.update_response_meta(self.pagination.get_item_meta(item, self))


class GenericModelView(ModelView):
    """Base class for API views implementing CRUD methods.

    `GenericModelView` provides basic implementations of the standard CRUD
    HTTP methods using the methods implemented in `ModelView`.

    In simple APIs, most view classes will extend `GenericModelView`, and will
    declare methods that immediately call the methods here.
    ::

        class WidgetViewBase(GenericModelView):
            model = models.Widget
            schema = models.WidgetSchema()


        class WidgetListView(WidgetViewBase):
            def get(self):
                return self.list()

            def post(self):
                return self.create()


        class WidgetView(WidgetViewBase):
            def get(self, id):
                return self.retrieve(id)

            def patch(self, id):
                return self.update(id, partial=True)

            def delete(self, id):
                return self.destroy(id)

    To extend or otherwise customize the behavior of the methods here, override
    the methods in `MethodView`.
    """

    def list(self):
        """Return a list of items.

        This is the standard GET handler on a list view.

        :return: An HTTP 200 response.
        :rtype: :py:class:`flask.Response`
        """
        items = self.get_list()
        return self.make_items_response(items)

    def retrieve(self, id, *, create_transient_stub=False):
        """Retrieve an item by ID.

        This is the standard ``GET`` handler on a detail view.

        :param id: The item ID.
        :param bool create_transient_stub: If set, create and retrieve a
            transient stub for the item if it is not found. This will not save
            the stub to the database.
        :return: An HTTP 200 response.
        :rtype: :py:class:`flask.Response`
        """
        item = self.get_item_or_404(
            id, create_transient_stub=create_transient_stub
        )
        return self.make_item_response(item)

    def create(self, *, allow_client_id=False):
        """Create a new item using the request data.

        This is the standard ``POST`` handler on a list view.

        :param bool allow_client_id: If set, allow the client to specify ID
            fields for the item.
        :return: An HTTP 201 response.
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
        *,
        with_for_update=False,
        partial=False,
    ):
        """Update the item for the specified ID with the request data.

        This is the standard ``PUT`` handler on a detail view if `partial` is
        not set, or the standard ``PATCH`` handler if `partial` is set.

        :param id: The item ID.
        :param bool with_for_update: If set, lock the item row while updating
            using ``FOR UPDATE``.
        :param bool partial: If set, perform a partial update for the item,
            ignoring fields marked ``required`` on `deserializer`.
        :return: An HTTP 200 response.
        :rtype: :py:class:`flask.Response`
        """
        item = self.get_item_or_404(id, with_for_update=with_for_update)
        data_in = self.get_request_data(expected_id=id, partial=partial)

        item = self.update_item(item, data_in) or item
        self.commit()

        return self.make_item_response(item)

    def upsert(self, id, *, with_for_update=False):
        """Upsert the item for the specified ID with the request data.

        This will update the item for the given ID, if that item exists.
        Otherwise, this will create a new item with the request data.

        :param id: The item ID.
        :param bool with_for_update: If set, lock the item row while updating
            using ``FOR UPDATE``.
        :return: An HTTP 200 or 201 response.
        :rtype: :py:class:`flask.Response`
        """
        data_in = self.get_request_data(expected_id=id)

        try:
            item = self.get_item(id, with_for_update=with_for_update)
        except NoResultFound:
            item = self.create_and_add_item(data_in)
            self.commit()

            return self.make_created_response(item)
        else:
            item = self.update_item(item, data_in) or item
            self.commit()

            return self.make_item_response(item)

    def destroy(self, id):
        """Delete the item for the specified ID.

        :param id: The item ID.
        :return: An HTTP 204 response.
        :rtype: :py:class:`flask.Response`
        """
        item = self.get_item_or_404(id)

        item = self.delete_item(item) or item
        self.commit()

        return self.make_deleted_response(item)
