import base64

import flask
from marshmallow import ValidationError
import sqlalchemy as sa

from . import meta
from .exceptions import ApiError
from .utils import if_none, iter_validation_errors

# -----------------------------------------------------------------------------


class PaginationBase(object):
    """A declarative specification of how LIMIT should be applied to queries
    originating from a particular :py:class:`ModelView` to divide the results
    of those queries into pages. Subclasses must implement :py:meth:`get_page`
    to provide the pagination logic.
    """

    def get_page(self, query, view):
        """Apply pagination criteria to the provided `query`.

        :param query: The query to paginate.
        :type query: :py:class:`sqlalchemy.orm.query.Query`
        :param view: The view with the model we wish to paginate.
        :type view: :py:class:`ModelView`
        :return: The paginated query
        :rtype: :py:class:`sqlalchemy.orm.query.Query`
        :raises: A :py:class:`NotImplementedError` if no implementation is
            provided.
        """
        raise NotImplementedError()

    def get_item_meta(self, item, view):
        """Retrieve a value to interpolate under the `meta` key of the response.

        :param item: An instance of the :py:attr:`ModelView.model`.
        :type item: obj
        :param view: The view with the :py:attr:`ModelView.model`.
        :type view: :py:class:`ModelView`
        """
        return None


# -----------------------------------------------------------------------------


class LimitPaginationBase(PaginationBase):
    """A pagination scheme that uses a scalar value to apply a limit to
    queries originating from a particular :py:class:`ModelView`. Subclasses
    must implement :py:meth:`get_limit` to provide the LIMIT value.
    """

    def get_page(self, query, view):
        """Uses the scalar value from :py:meth:`get_limit` to set the LIMIT
        on `query`. If the number of available items exceeds the LIMIT the
        response will have ``has_next_page`` set to ``True`` under the meta
        key. Otherwise, this value is set to ``False``.

        :param query: The query to paginate.
        :type query: :py:class:`sqlalchemy.orm.query.Query`
        :param view: The view with the model we wish to paginate.
        :type view: :py:class:`ModelView`
        :return: The items from the paginated query
        :rtype: list
        """
        limit = self.get_limit()
        if limit is not None:
            query = query.limit(limit + 1)

        items = query.all()

        if limit is not None and len(items) > limit:
            has_next_page = True
            items = items[:limit]
        else:
            has_next_page = False

        meta.update_response_meta({'has_next_page': has_next_page})
        return items

    def get_limit(self):
        """Returns the scalar LIMIT value.

        :rtype: int
        :raises: A :py:class:`NotImplementedError` if no implementation is
            provided.
        """
        raise NotImplementedError()


class MaxLimitPagination(LimitPaginationBase):
    """A pagination scheme that sets an upper bound on the number of retrieved
    items.

    :param int max_limit: The maximum number of items to retrieve
    """

    def __init__(self, max_limit):
        self._max_limit = max_limit

    def get_limit(self):
        """Returns the stored limit.

        :return: The maximum number of items to retrieve.
        :rtype: int
        """
        return self._max_limit


class LimitPagination(LimitPaginationBase):
    """A pagination scheme that inspects the :py:attr:`limit_arg` query
    parameter to apply a LIMIT value to queries origination from a particular
    :py:class:`ModelView`. If no limit is provided the `default_limit` will be
    applied to each query. The `max_limit` can set an upper bound on the LIMIT
    value. The `default_limit` must be less than or equal to the `max_limit`.

    :param int default_limit: The LIMIT value if none is provided in the request args
    :param int max_limit: The maximum LIMIT value
    """

    #: The name of the query parameter to inspect for the LIMIT value.
    limit_arg = 'limit'

    def __init__(self, default_limit=None, max_limit=None):
        self._default_limit = if_none(default_limit, max_limit)
        self._max_limit = max_limit

        if self._max_limit is not None:
            assert self._default_limit <= self._max_limit, (
                "default limit exceeds max limit"
            )

    def get_limit(self):
        """Retrieve the limit value from the :py:attr:`flask.Request.args`.

        :raises: An :py:class:`ApiError` if the limit cannot be parsed.
        """
        limit = flask.request.args.get(self.limit_arg)
        try:
            return self.parse_limit(limit)
        except ApiError as e:
            raise e.update({'source': {'parameter': self.limit_arg}})

    def parse_limit(self, limit):
        """Parses the given `limit` as an integer. If no `limit` is provided,
        the stored default limit will be returned. The parsed `limit` will be
        no larger than the stored maximum limit.

        :param str limit: The raw LIMIT value
        :returns: The parsed LIMIT value
        :rtype: int
        :raises: An :py:class:`ApiError` if the limit cannot be parsed as an
            integer or if it is less than ``0``.
        """
        if limit is None:
            return self._default_limit

        try:
            limit = int(limit)
        except ValueError:
            raise ApiError(400, {'code': 'invalid_limit'})
        if limit < 0:
            raise ApiError(400, {'code': 'invalid_limit'})

        if self._max_limit is not None:
            limit = min(limit, self._max_limit)

        return limit

    def spec_declaration(self, path, spec, **kwargs):
        path['get'].add_parameter(
            name='limit',
            type='int',
            description="pagination limit",
        )
        path['get'].add_property_to_response(
            prop_name='meta',
            type='object',
            properties={
                'has_next_page': {'type': 'boolean'},
            },
        )


class LimitOffsetPagination(LimitPagination):
    """A pagination scheme that inspects the :py:attr:`offset_arg` query
    parameter to apply an OFFSET value to queries originating from a
    particular :py:class:`ModelView`. The pagination logic is composed with
    :py:class:`LimitPagination` allowing arbitrary pages to be retrieved.
    """

    #: The name of the query parameter to inspect for the OFFSET value.
    offset_arg = 'offset'

    def get_page(self, query, view):
        """Uses the offset value from :py:meth:`get_offset` to set the OFFSET
        on `query`. 

        :param query: The query to paginate.
        :type query: :py:class:`sqlalchemy.orm.query.Query`
        :param view: The view with the model we wish to paginate.
        :type view: :py:class:`ModelView`
        :return: The items from the paginated query
        :rtype: list
        """
        offset = self.get_offset()
        query = query.offset(offset)
        return super(LimitOffsetPagination, self).get_page(query, view)

    def get_offset(self):
        """Retrieve the offset value from the :py:attr:`flask.Request.args`.

        :raises: An :py:class:`ApiError` if the offset cannot be parsed.
        """
        offset = flask.request.args.get(self.offset_arg)
        try:
            return self.parse_offset(offset)
        except ApiError as e:
            raise e.update({'source': {'parameter': self.offset_arg}})

    def parse_offset(self, offset):
        """Parses the given `offset` as an integer. If no `offset` is provided,
        the default offset ``0`` will be returned.

        :param str offset: The raw OFFSET value
        :returns: The parsed OFFSET value
        :rtype: int
        :raises: An :py:class:`ApiError` if the offset cannot be parsed as an
            integer or if it is less than ``0``.
        """
        if offset is None:
            return 0

        try:
            offset = int(offset)
        except ValueError:
            raise ApiError(400, {'code': 'invalid_offset'})
        if offset < 0:
            raise ApiError(400, {'code': 'invalid_offset'})

        return offset

    def spec_declaration(self, path, spec, **kwargs):
        super(LimitOffsetPagination, self).spec_declaration(path, spec)

        path['get'].add_parameter(
            name='offset',
            type='int',
            description="pagination offset",
        )


class PagePagination(LimitOffsetPagination):
    """A pagination scheme that abstracts the LIMIT and OFFSET values in
    terms of `page_size` and `page` respectively.

    :param int page_size: The number of items to return in each page.
    """

    #: The name of the query parameter to inspect for the page value.
    page_arg = 'page'

    def __init__(self, page_size):
        super(PagePagination, self).__init__()
        self._page_size = page_size

    def get_offset(self):
        """The offset of a particular page, computed as follows::

            offset = page * page_size

        :raises: An :py:class:`ApiError` if the page cannot be parsed.
        """
        return self.get_request_page() * self._page_size

    def get_request_page(self):
        """Retrieve the page value from the :py:attr:`flask.Request.args`.

        :raises: An :py:class:`ApiError` if the page cannot be parsed.
        """
        page = flask.request.args.get(self.page_arg)
        try:
            return self.parse_page(page)
        except ApiError as e:
            raise e.update({'source': {'parameter': self.page_arg}})

    def parse_page(self, page):
        """Parses the given `page` as an integer. If no `page` is provided,
        the default page ``0`` will be returned.

        :param str offset: The raw page value
        :returns: The parsed page value
        :rtype: int
        :raises: An :py:class:`ApiError` if the page cannot be parsed as an
            integer or if it is less than ``0``.
        """
        if page is None:
            return 0

        try:
            page = int(page)
        except ValueError:
            raise ApiError(400, {'code': 'invalid_page'})
        if page < 0:
            raise ApiError(400, {'code': 'invalid_page'})

        return page

    def get_limit(self):
        """Retrieve the limit value, which is fixed to the stored `page_size`."""
        return self._page_size

    def spec_declaration(self, path, spec, **kwargs):
        super(PagePagination, self).spec_declaration(path, spec)

        path['get'].add_parameter(
            name='page',
            type='int',
            description="page number",
        )


# -----------------------------------------------------------------------------


class CursorPaginationBase(LimitPagination):
    """A pagination scheme that abstracts the OFFSET value into an encoded
    cursor. :py:class:`LimitOffsetPagination` is not invariant on writes.
    If records are added or removed there is a chance that the page
    corresponding to a particular OFFSET will no longer contain a target value.
    By encoding a particular record into a cursor it can be referenced as an
    OFFSET in the future even if the collection has been modified.

    For more information about cursor-based pagination see
    https://developers.facebook.com/docs/graph-api/using-graph-api.
    """

    #: The name of the query parameter to inspect for the cursor value.
    cursor_arg = 'cursor'

    def ensure_query_sorting(self, query, view):
        """Apply the sort order specified in :py:attr:`ModelView.sorting` to
        the provided `query`.

        :param query: The query to paginate.
        :type query: :py:class:`sqlalchemy.orm.query.Query`
        :param view: The view with the model we wish to paginate.
        :type view: :py:class:`ModelView`
        :return: The sorted query & the field orderings
        :rtype: tuple
        """
        sorting_field_orderings, missing_field_orderings = (
            self.get_sorting_and_missing_field_orderings(view)
        )

        query = view.sorting.sort_query_by_fields(
            query,
            view,
            missing_field_orderings,
        )
        field_orderings = sorting_field_orderings + missing_field_orderings

        return query, field_orderings

    def get_field_orderings(self, view):
        """Retrieve and concatenate the explicit and implicit field orderings.
        See :py:meth:`get_criterion` for the structure of the field ordering type.

        :param view: The view with the model we wish to paginate.
        :type view: :py:class:`ModelView`
        :return: A sequence of field orderings
        :rtype: seq
        """
        sorting_field_orderings, missing_field_orderings = (
            self.get_sorting_and_missing_field_orderings(view)
        )
        return sorting_field_orderings + missing_field_orderings

    def get_sorting_and_missing_field_orderings(self, view):
        """Retrieve a tuple of two sequences of field orderings. The first
        sequence contains a field ordering for each of the sort fields passed
        in the request args. The second sequence contains a field ordering for
        each id field that was not passed in the request args as a sort field.

        Note that if an explicit sort is passed in the request args, then the
        missing fields will take on the the sort order of the explicit sort.

        See :py:meth:`get_criterion` for the structure of the field ordering type.

        :param view: The view with the model we wish to paginate.
        :type view: :py:class:`ModelView`
        :return: A tuple of field ordering sequences
        :rtype: tuple
        """
        sorting = view.sorting
        assert sorting is not None, (
            "sorting must be defined when using cursor pagination"
        )

        sorting_field_orderings = sorting.get_request_field_orderings(view)

        sorting_ordering_fields = frozenset(
            field_name for field_name, _ in sorting_field_orderings
        )

        # For convenience, use the ascending setting on the last explicit
        # ordering when possible, such that reversing the sort will reverse
        # the IDs as well.
        if sorting_field_orderings:
            last_field_asc = sorting_field_orderings[-1][1]
        else:
            last_field_asc = True

        missing_field_orderings = tuple(
            (id_field, last_field_asc) for id_field in view.id_fields
            if id_field not in sorting_ordering_fields
        )

        return sorting_field_orderings, missing_field_orderings

    def get_request_cursor(self, view, field_orderings):
        """Retrieve a cursor value that corresponds to the provided request
        args.

        :param view: The view with the model we wish to paginate.
        :type view: :py:class:`ModelView`
        :param field_orderings: A sequence of field_ordering tuples
        :type field_orderings: seq
        :return: A cursor value
        :rtype: str
        :raises: :py:class:`ApiError` if an invalid cursor is provided in
            `cursor_arg`.
        """
        cursor = flask.request.args.get(self.cursor_arg)
        if not cursor:
            return None

        try:
            return self.parse_cursor(cursor, view, field_orderings)
        except ApiError as e:
            raise e.update({'source': {'parameter': self.cursor_arg}})

    def parse_cursor(self, cursor, view, field_orderings):
        """Decode the given `cursor` to a list of its sorted fields.

        :param cursor: The encoded cursor
        :type cursor: str
        :param view: The view with the model we wish to paginate.
        :type view: :py:class:`ModelView`
        :param field_orderings: A sequence of field_ordering tuples
        :type field_orderings: seq
        :return: The sorted fields of the cursor
        :rtype: seq
        :raises: :py:class:`ApiError` if an invalid cursor is provided in
            `cursor_arg`.
        """
        cursor = self.decode_cursor(cursor)

        if len(cursor) != len(field_orderings):
            raise ApiError(400, {'code': 'invalid_cursor.length'})

        deserializer = view.deserializer
        column_fields = (
            deserializer.fields[field_name]
            for field_name, _ in field_orderings
        )

        try:
            cursor = tuple(
                field.deserialize(value)
                for field, value in zip(column_fields, cursor)
            )
        except ValidationError as e:
            raise ApiError(400, *(
                self.format_validation_error(message)
                for message, path in iter_validation_errors(e.messages)
            ))

        return cursor

    def decode_cursor(self, cursor):
        """Applies :py:meth:`decode_value` to each dot-separated value in the
        `cursor`.

        :param str cursor: A cursor value.
        :returns: The decoded field values in the cursor.
        :rtype: seq
        :raises: :py:class:`ApiError` if the cursor is invalid.
        """
        try:
            cursor = cursor.split('.')
            cursor = tuple(self.decode_value(value) for value in cursor)
        except (TypeError, ValueError):
            raise ApiError(400, {'code': 'invalid_cursor.encoding'})

        return cursor

    def decode_value(self, value):
        """Decodes the given `value` according to the following scheme:

        1. The value is encoded as `ascii`.
        2. Any missing padding is added to the end of the encoded value.
        3. :py:func:`base64.urlsafe_b64decode` is applied to the value.
        4. The value is decoded as `utf-8`.

        :param value: An arbitrary value
        :returns: The encoded value
        :rtype: str
        """
        value = value.encode('ascii')
        value += (3 - ((len(value) + 3) % 4)) * b'='  # Add back padding.
        value = base64.urlsafe_b64decode(value)
        return value.decode()

    def format_validation_error(self, message):
        """Create a dictionary that describes the validation error provided in
        `message`. The response body has the following structure::

            code:
                type: string
                description: Always the literal `invalid_cursor`
            detail:
                type: string
                description: The message in `message`

        :return: The formatted validation error
        :rtype: dict
        """
        return {
            'code': 'invalid_cursor',
            'detail': message,
        }

    def get_filter(self, view, field_orderings, cursor):
        """Construct a filter clause that retrieves the page corresponding
        to the provided `cursor`.

        :param view: The view with the model we wish to paginate.
        :type view: :py:class:`ModelView`
        :param field_orderings: A sequence of field_ordering tuples
        :type field_orderings: seq
        :param cursor: A set of values corresponding to the fields in `field_orderings`
        :type cursor: seq
        :return: A filter clause
        """
        sorting = view.sorting

        column_cursors = tuple(
            (sorting.get_column(view, field_name), asc, value)
            for (field_name, asc), value in zip(field_orderings, cursor)
        )

        return sa.or_(
            self.get_filter_clause(column_cursors[:i + 1])
            for i in range(len(column_cursors))
        )

    def get_filter_clause(self, column_cursors):
        """Construct a filter clause that retrieves the page corresponding to
        the specification in `column_cursors`.

        :param column_cursors: A tuple of tuples (column, sort_order, value)
        :type column_cursors: tuple
        :return: A filter clause
        """
        previous_clauses = sa.and_(
            column == value for column, _, value in column_cursors[:-1]
        )

        column, asc, value = column_cursors[-1]
        if asc:
            current_clause = column > value
        else:
            current_clause = column < value

        return sa.and_(previous_clauses, current_clause)

    def make_cursors(self, items, view, field_orderings):
        """Create a cursor for each item in `items`. See :py:meth:`make_cursor`.

        :param seq items: A sequence of instances of :py:attr:`ApiView.model`
        :param view: The view we wish to paginate.
        :type view: :py:class:`ModelView`
        :param seq field_orderings: A sequence of (field, asc?).
        :return: A sequence of :py:class:`marshmallow.Field`.
        :rtype: seq
        """
        column_fields = self.get_column_fields(view, field_orderings)
        return tuple(
            self.render_cursor(item, column_fields) for item in items
        )

    def make_cursor(self, item, view, field_orderings):
        """Create a cursor for the given `item` by encoding an ordered list
        of its sorted fields.

        :param obj item: An instance :py:attr:`ApiView.model`
        :param view: The view we wish to paginate.
        :type view: :py:class:`ModelView`
        :param seq field_orderings: A sequence of (field, asc?).
        :return: A sequence of :py:class:`marshmallow.Field`.
        :rtype: seq
        """
        column_fields = self.get_column_fields(view, field_orderings)
        return self.render_cursor(item, column_fields)

    def get_column_fields(self, view, field_orderings):
        """Retrieve the :py:class:`marshmallow.Field` corresponding to each
        sorted column in the order specified by field_orderings.

        :param view: The view we wish to paginate.
        :type view: :py:class:`ModelView`.
        :param seq field_orderings: A sequence of (field, asc?).
        :return: A sequence of :py:class:`marshmallow.Field`.
        :rtype: seq
        """
        serializer = view.serializer
        return tuple(
            serializer.fields[field_name]
            for field_name, _ in field_orderings
        )

    def render_cursor(self, item, column_fields):
        """Encode the given `item` into a cursor according to the serialized
        values of the fields provided in `column_fields`.

        :param obj item: The cursor's target item.
        :param seq column_fields: The fields to serialize to derive a unique value
            for the cursor.
        :returns: The rendered cursor.
        :rtype: str
        """
        cursor = tuple(
            field._serialize(getattr(item, field.name), field.name, item)
            for field in column_fields
        )

        return self.encode_cursor(cursor)

    def encode_cursor(self, cursor):
        """Applies :py:meth:`encode_value` to each value in the `cursor`. The
        encoded values are concatenated together with ``.``

        :param seq cursor: A sequence of arbitrary values
        :returns: The encoded cursor
        :rtype: str
        """
        return '.'.join(self.encode_value(value) for value in cursor)

    def encode_value(self, value):
        """Encodes the given `value` according to the following scheme:

        1. The value is encoded as `utf-8`.
        2. :py:func:`base64.urlsafe_b64encode` is applied to the value.
        3. Padding is removed from the end of the encoded value.
        4. The value is decoded as `ascii`.

        :param value: An arbitrary value
        :returns: The encoded value
        :rtype: str
        """
        value = str(value)
        value = value.encode()
        value = base64.urlsafe_b64encode(value)
        value = value.rstrip(b'=')  # Strip padding.
        return value.decode('ascii')

    def spec_declaration(self, path, spec, **kwargs):
        super(CursorPaginationBase, self).spec_declaration(path, spec)

        path['get'].add_parameter(
            name='cursor',
            type='string',
            description="pagination cursor",
        )


class RelayCursorPagination(CursorPaginationBase):
    """A pagination scheme that is compatible with the Relay web framework.

    For more information about the Relay pagination interface see
    https://facebook.github.io/relay/graphql/connections.htm.
    """

    def get_page(self, query, view):
        """Apply the pagination criteria to the provided `query` and retrieve
        a sequence of corresponding items. Provides a cursor for each item in
        the response metadata.

        :param query: The query to paginate.
        :type query: :py:class:`sqlalchemy.orm.query.Query`
        :param view: The view with the model we wish to paginate.
        :type view: :py:class:`ModelView`
        :return: The paginated query
        :rtype: :py:class:`sqlalchemy.orm.query.Query`
        """
        query, field_orderings = self.ensure_query_sorting(query, view)

        cursor_in = self.get_request_cursor(view, field_orderings)
        if cursor_in is not None:
            query = query.filter(
                self.get_filter(view, field_orderings, cursor_in),
            )

        items = super(RelayCursorPagination, self).get_page(query, view)

        # Relay expects a cursor for each item.
        cursors_out = self.make_cursors(items, view, field_orderings)
        meta.update_response_meta({'cursors': cursors_out})

        return items

    def get_item_meta(self, item, view):
        """Construct metadata for the provided `item` by retrieving its
        corresponding cursor. The metadata has the following structure::

            cursor:
                type: string
                description: The cursor corresponding to the given `item`

        :param item: An instance of the :py:attr:`ModelView.model`.
        :type item: obj
        :param view: The view with the :py:attr:`ModelView.model`.
        :type view: :py:class:`ModelView`
        :return: The item metadata
        :rtype: dict
        """
        field_orderings = self.get_field_orderings(view)

        cursor = self.make_cursor(item, view, field_orderings)
        return {'cursor': cursor}
