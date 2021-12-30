import base64
from dataclasses import dataclass
from typing import Any, List, Tuple, Union

import flask
import sqlalchemy as sa
from marshmallow import ValidationError, fields

from flask_resty.sorting import FieldOrderings, FieldSortingBase
from flask_resty.view import ModelView

from . import meta
from .exceptions import ApiError
from .utils import if_none

# -----------------------------------------------------------------------------


class PaginationBase:
    """The base class for pagination components.

    Pagination components control the list view fetches individual pages of
    data, as opposed to the full collection. They handle limiting the number
    of returned records, and fetching additional records after the initial
    page.

    Subclasses must implement :py:meth:`get_page` to provide the pagination
    logic.
    """

    def adjust_sort_ordering(
        self, view, field_orderings: FieldOrderings
    ) -> FieldOrderings:
        return field_orderings

    def get_page(self, query, view):
        """Restrict the specified query to a single page.

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
        """Build pagination metadata for a single item.

        :param item: An instance of the :py:attr:`ModelView.model`.
        :type item: obj
        :param view: The view with the :py:attr:`ModelView.model`.
        :type view: :py:class:`ModelView`
        """
        return None


# -----------------------------------------------------------------------------


class LimitPaginationBase(PaginationBase):
    """The base scheme for pagination components that limit fetched item count.

    The pagination metadata will indicate the presence of additional items with
    the ``has_next_page`` property.

    Subclasses must implement :py:meth:`get_limit` to provide maximum number
    of returned items.
    """

    def get_page(self, query, view) -> List:
        limit = self.get_limit()
        if limit is not None:
            query = query.limit(limit + 1)

        items = query.all()

        if limit is not None and len(items) > limit:
            has_next_page = True
            items = items[:limit]
        else:
            has_next_page = False

        meta.update_response_meta({"has_next_page": has_next_page})
        return items

    def get_limit(self):
        """Override this method to return the maximum number of returned items.

        :rtype: int
        """
        raise NotImplementedError()


class MaxLimitPagination(LimitPaginationBase):
    """Return up to a fixed maximum number of items.

    This is not especially useful and is included only for completeness.

    :param int max_limit: The maximum number of items to retrieve.
    """

    def __init__(self, max_limit):
        self._max_limit = max_limit

    def get_limit(self):
        return self._max_limit


class LimitPagination(LimitPaginationBase):
    """A pagination scheme that takes a user-specified limit.

    This is not especially useful and is included only for completeness.

    This pagination scheme uses the :py:attr:`limit_arg` query parameter to
    limit the number of items returned by the query.

    If no such limit is explicitly specified, this uses `default_limit`. If
    `max_limit` is specified, then the user-specified limit may not exceed
    `max_limit`.

    :param int default_limit: The default maximum number of items to retrieve,
        if the user does not specify an explicit value.
    :param int max_limit: The maximum number of items the user is allowed to
        request.
    """

    #: The name of the query parameter to inspect for the LIMIT value.
    limit_arg = "limit"

    def __init__(self, default_limit=None, max_limit=None):
        self._default_limit = if_none(default_limit, max_limit)
        self._max_limit = max_limit

        if self._max_limit is not None:
            assert (
                self._default_limit <= self._max_limit
            ), "default limit exceeds max limit"

    def get_limit(self):
        limit = flask.request.args.get(self.limit_arg)
        try:
            return self.parse_limit(limit)
        except ApiError as e:
            raise e.update({"source": {"parameter": self.limit_arg}})

    def parse_limit(self, limit):
        if limit is None:
            return self._default_limit

        try:
            limit = int(limit)
        except ValueError as e:
            raise ApiError(400, {"code": "invalid_limit"}) from e
        if limit < 0:
            raise ApiError(400, {"code": "invalid_limit"})

        if self._max_limit is not None:
            limit = min(limit, self._max_limit)

        return limit


class LimitOffsetPagination(LimitPagination):
    """A pagination scheme that takes a user-specified limit and offset.

    This pagination scheme takes a user-specified limit and offset. It will
    retrieve up to the specified number of items, beginning at the specified
    offset.
    """

    #: The name of the query parameter to inspect for the OFFSET value.
    offset_arg = "offset"

    def get_page(self, query, view):
        offset = self.get_offset()
        query = query.offset(offset)
        return super().get_page(query, view)

    def get_offset(self):
        offset = flask.request.args.get(self.offset_arg)
        try:
            return self.parse_offset(offset)
        except ApiError as e:
            raise e.update({"source": {"parameter": self.offset_arg}})

    def parse_offset(self, offset):
        if offset is None:
            return 0

        try:
            offset = int(offset)
        except ValueError as e:
            raise ApiError(400, {"code": "invalid_offset"}) from e
        if offset < 0:
            raise ApiError(400, {"code": "invalid_offset"})

        return offset


class PagePagination(LimitOffsetPagination):
    """A pagination scheme that fetches a particular fixed-size page.

    This works similar to `LimitOffsetPagination`. The limit used will always
    be the fixed page size. The offset will be page * page_size.

    :param int page_size: The fixed number of items per page.
    """

    #: The name of the query parameter to inspect for the page value.
    page_arg = "page"

    def __init__(self, page_size):
        super().__init__()
        self._page_size = page_size

    def get_offset(self):
        return self.get_request_page() * self._page_size

    def get_request_page(self):
        page = flask.request.args.get(self.page_arg)
        try:
            return self.parse_page(page)
        except ApiError as e:
            raise e.update({"source": {"parameter": self.page_arg}})

    def parse_page(self, page):
        if page is None:
            return 0

        try:
            page = int(page)
        except ValueError as e:
            raise ApiError(400, {"code": "invalid_page"}) from e
        if page < 0:
            raise ApiError(400, {"code": "invalid_page"})

        return page

    def get_limit(self):
        return self._page_size


# -----------------------------------------------------------------------------

Cursor = Tuple[Any, ...]


@dataclass
class CursorInfo:
    reversed: bool

    cursor: Union[str, None]
    cursor_arg: Union[str, None]

    limit: Union[str, None]
    limit_arg: Union[str, None]


class CursorPaginationBase(LimitPagination):
    """The base class for pagination schemes that use cursors.

    Unlike with offsets that identify items by relative position, cursors
    identify position by content. This allows continuous pagination without
    concerns about page shear on dynamic collections. This makes cursor-based
    pagination especially effective for lists with infinite scroll dynamics,
    as offset-based pagination can miss or duplicate items due to inserts or
    deletes.

    It's also more efficient against the database, as the cursor condition can
    be cheaply evaluated as a filter against an index.

    :param bool validate: If unset, bypass validation on cursor values. This is
        useful if the deserializer field imposes validation that will fail for
        on cursor values for items actually present.
    """

    #: The name of the query parameter to inspect for the cursor value.
    cursor_arg = "cursor"
    limit_arg = "limit"

    #: the name of the query parameter to inspect for explicit forward pagination
    after_arg = "after"
    first_arg = "first"

    #: the name of the query parameter to inspect for explicit backward pagination
    before_arg = "before"
    last_arg = "last"

    def __init__(self, *args, validate_values=True, **kwargs):
        super().__init__(*args, **kwargs)
        self._validate_values = validate_values

    def try_get_arg(self, arg):
        value = flask.request.args.get(arg)
        if value is not None:
            return (value, arg)

        return (None, None)

    # There are a number of different cases that this covers in order to be backwards compatible with
    def get_cursor_info(self) -> CursorInfo:
        cursor = None
        cursor_arg = None

        limit = None
        limit_arg = None

        # Unambiguous cases where a cursor is provided.
        if self.after_arg in flask.request.args:
            reversed = False
            cursor, cursor_arg = self.try_get_arg(self.after_arg)
            limit, limit_arg = self.try_get_arg(self.first_arg)

        elif self.before_arg in flask.request.args:
            reversed = True
            cursor, cursor_arg = self.try_get_arg(self.before_arg)
            limit, limit_arg = self.try_get_arg(self.last_arg)

        # Ambiguous cases where limits are provided but not cursors
        # Relay sometimes sends both first and after, default to "first"
        # in keeping with the cursor precedence
        elif self.first_arg in flask.request.args:
            reversed = False
            limit, limit_arg = self.try_get_arg(self.first_arg)

        elif self.last_arg in flask.request.args:
            reversed = True
            limit, limit_arg = self.try_get_arg(self.last_arg)
        # legacy "cursor_arg" config cases always map to after/first
        else:
            reversed = False
            cursor, cursor_arg = self.try_get_arg(self.cursor_arg)
            limit, limit_arg = self.try_get_arg(self.limit_arg)

        return CursorInfo(reversed, cursor, cursor_arg, limit, limit_arg)

    def get_limit(self):
        cursor_info = self.get_cursor_info()

        try:
            return self.parse_limit(cursor_info.limit)
        except ApiError as e:
            raise e.update({"source": {"parameter": cursor_info.limit_arg}})

    @property
    def reversed(self):
        return self.get_cursor_info().reversed

    def adjust_sort_ordering(
        self, view: ModelView, field_orderings
    ) -> FieldOrderings:
        """Ensure the query is sorted correctly and get the field orderings.

        The implementation of cursor-based pagination in Flask-RESTy requires
        that the query be sorted in a fully deterministic manner. The timestamp
        columns usually used in sorting do not quite qualify, as two different
        rows can have the same timestamp. This method adds the ID fields to the
        sorting criterion, then returns the field orderings for use in the
        other methods, as in `get_field_orderings` below.

        :param view: The view with the model we wish to paginate.
        :type view: :py:class:`ModelView`
        :return: The field orderings necessary to do cursor pagination deterministically
        :rtype: FieldOrderings
        """

        # ignore the passed in sort so that it's consistent
        # with further calls in get_page
        return self.get_field_orderings(view)

    def get_field_orderings(self, view: ModelView):
        sorting: FieldSortingBase = view.sorting

        assert (
            sorting is not None
        ), "sorting must be defined when using cursor pagination"

        sorting_field_orderings = sorting.get_request_field_orderings(view)
        sorting_ordering_fields = frozenset(
            field_name for field_name, _ in sorting_field_orderings
        )

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
            (id_field, last_field_asc)
            for id_field in view.id_fields
            if id_field not in sorting_ordering_fields
        )

        field_ordering = sorting_field_orderings + missing_field_orderings

        if self.reversed:
            field_ordering = tuple(
                (field, not order) for field, order in field_ordering
            )

        return field_ordering

    def get_request_cursor(self, view, field_orderings):
        """Get the cursor value specified in the request.

        Given the view and the field_orderings as above, this method will read
        the encoded cursor from the query, then return the cursor as a tuple of
        the field values in the cursor.

        This parsed cursor can then be used in `get_filter`.

        :param view: The view with the model we wish to paginate.
        :type view: :py:class:`ModelView`
        :param field_orderings: A sequence of field_ordering tuples
        :type field_orderings: seq
        :return: A cursor value
        :rtype: str
        :raises: :py:class:`ApiError` if an invalid cursor is provided in
            `cursor_arg`.
        """

        cursor_info = self.get_cursor_info()

        if cursor_info.cursor is None:
            return None

        try:
            return self.parse_cursor(view, cursor_info.cursor, field_orderings)
        except ApiError as e:
            raise e.update({"source": {"parameter": cursor_info.cursor_arg}})

    def parse_cursor(
        self,
        view: ModelView,
        cursor: str,
        field_orderings: FieldOrderings,
    ) -> Cursor:
        cursor = self.decode_cursor(cursor)

        if len(cursor) != len(field_orderings):
            raise ApiError(400, {"code": "invalid_cursor.length"})

        deserializer = view.deserializer
        column_fields = (
            deserializer.fields[field_name]
            for field_name, _ in field_orderings
        )

        try:
            cursor = tuple(
                self.deserialize_value(field, value)
                for field, value in zip(column_fields, cursor)
            )
        except ValidationError as e:
            raise ApiError.from_validation_error(
                400, e, self.format_validation_error
            ) from e

        return cursor

    def decode_cursor(self, cursor: str) -> Tuple[str, ...]:
        try:
            cursor = cursor.split(".")
            cursor = tuple(self.decode_value(value) for value in cursor)
        except (TypeError, ValueError) as e:
            raise ApiError(400, {"code": "invalid_cursor.encoding"}) from e

        return cursor

    def decode_value(self, value: str):
        value = value.encode("ascii")
        value += (3 - ((len(value) + 3) % 4)) * b"="  # Add back padding.
        value = base64.urlsafe_b64decode(value)
        return value.decode()

    def deserialize_value(self, field, value):
        return (
            field.deserialize(value)
            if self._validate_values
            # Cursors don't need to be fully valid values; they just need to be
            #  the correct type for sorting, so it can make sense to bypass
            #  validation.
            else field._deserialize(value, None, None)
        )

    def format_validation_error(self, message, path):
        return {"code": "invalid_cursor", "detail": message}

    def get_filter(
        self, view, field_orderings: FieldOrderings, cursor: Cursor
    ):
        """Build the filter clause corresponding to a cursor.

        Given the field orderings and the cursor as above, this will construct
        a filter clause that can be used to filter a query to return only items
        after the specified cursor, per the specified field orderings. Use this
        to apply the equivalent of the offset specified by the cursor.

        :param view: The view with the model we wish to paginate.
        :type view: :py:class:`ModelView`
        :param field_orderings: A sequence of field_ordering tuples derived from the view's Sorting with explicit id ordering
        :type field_orderings: seq
        :param cursor: A set of values corresponding to the fields in
            `field_orderings`
        :type cursor: seq
        :return: A filter clause
        """
        sorting: FieldSortingBase = view.sorting

        column_cursors = tuple(
            (sorting.get_column(view, field_name), asc, value)
            for (field_name, asc), value in zip(field_orderings, cursor)
        )

        return sa.or_(
            self.get_filter_clause(column_cursors[: i + 1])
            for i in range(len(column_cursors))
        )

    def get_filter_clause(self, column_cursors):
        previous_clauses = sa.and_(
            column == value for column, _, value in column_cursors[:-1]
        )

        column, asc, value = column_cursors[-1]

        # SQL Alchemy won't let you > or < a boolean, so we convert
        # to an integer, the DB's seem to handle this just fine
        if isinstance(value, bool):
            column = sa.cast(column, sa.Integer)
            value = int(value)

        if asc:
            current_clause = column > value
        else:
            current_clause = column < value

        return sa.and_(previous_clauses, current_clause)

    def make_cursors(self, items, view, field_orderings):
        """Build a cursor for each of many items.

        This method creates a cursor for each item in `items`. It produces the
        same cursors as :py:meth:`make_cursor`, but is slightly more efficient
        in cases where cursors for multiple items are required.

        :param seq items: A sequence of instances of :py:attr:`ApiView.model`
        :param view: The view we wish to paginate.
        :type view: :py:class:`ModelView`
        :param seq field_orderings: A sequence of (field, asc?).
        :return: A sequence of :py:class:`marshmallow.Field`.
        :rtype: seq
        """
        column_fields = self.get_column_fields(view, field_orderings)
        return tuple(self.render_cursor(item, column_fields) for item in items)

    def make_cursor(self, item, view, field_orderings):
        """Build a cursor for a given item.

        Given an item and the field orderings as above, this builds a cursor
        for the item. This cursor encodes the value for each field on the item
        per the specified field orderings.

        This cursor should be returned in page or item metadata to allow
        pagination continuing after the cursor for the item.

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
        serializer = view.serializer
        return tuple(
            serializer.fields[field_name] for field_name, _ in field_orderings
        )

    def render_cursor(self, item, column_fields):
        cursor = tuple(
            field._serialize(getattr(item, field.name), field.name, item)
            for field in column_fields
        )

        return self.encode_cursor(cursor)

    def encode_cursor(self, cursor):
        return ".".join(self.encode_value(value) for value in cursor)

    def encode_value(self, value):
        value = str(value)
        value = value.encode()
        value = base64.urlsafe_b64encode(value)
        value = value.rstrip(b"=")  # Strip padding.
        return value.decode("ascii")


class RelayCursorPagination(CursorPaginationBase):
    """A pagination scheme that works with the Relay specification.

    This pagination scheme assigns a cursor to each retrieved item. The page
    metadata will contain an array of cursors, one per item. The item metadata
    will include the cursor for the fetched item.

    For Relay Cursor Connections Specification, see
    https://facebook.github.io/relay/graphql/connections.htm.
    """

    def __init__(
        self,
        *args,
        page_info_arg=None,
        default_include_page_info=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self._default_include_page_info = default_include_page_info
        self.page_info_arg = page_info_arg

    def get_page_info(self, query, view, field_orderings, cursor):
        include_page_info = (
            self.deserialize_value(
                fields.Boolean(),
                flask.request.args.get(
                    self.page_info_arg, self._default_include_page_info
                ),
            )
            if self.page_info_arg
            else self._default_include_page_info
        )

        if not include_page_info:
            return {}

        total = query.count()

        index = 0
        if cursor:
            filter_clause = self.get_filter(
                view,
                tuple((field, not order) for field, order in field_orderings),
                cursor,
            )
            index = query.filter(filter_clause).count()

        # in the reversed case, both the order by and sort of inverted.
        # so in practice this gives us a reverse index, e.g. distance from
        # the end of the list. We normalize it back by subtracting from the total
        if self.reversed:
            index = max(total - index - 1, 0)

        return {"index": index, "total": total}

    def get_page(self, query, view):
        field_orderings = self.get_field_orderings(view)

        cursor_in = self.get_request_cursor(view, field_orderings)

        page_query = query
        if cursor_in is not None:
            page_query = page_query.filter(
                self.get_filter(view, field_orderings, cursor_in)
            )

        items = super().get_page(page_query, view)

        if self.reversed:
            items.reverse()

        # Relay expects a cursor for each item.
        cursors_out = self.make_cursors(items, view, field_orderings)

        page_info = self.get_page_info(query, view, field_orderings, cursor_in)

        meta.update_response_meta({"cursors": cursors_out, **page_info})

        return items

    def get_item_meta(self, item, view):

        cursor = self.make_cursor(item, view, self.get_field_orderings(view))
        return {"cursor": cursor}
