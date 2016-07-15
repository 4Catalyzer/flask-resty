import base64
import flask
from marshmallow import ValidationError
import sqlalchemy as sa
from sqlalchemy import Column, sql

from .exceptions import ApiError
from . import meta
from . import utils

# -----------------------------------------------------------------------------


class PaginationBase(object):
    def get_page(self, query, view):
        raise NotImplementedError()

    def get_item_meta(self, item, view):
        return None


# -----------------------------------------------------------------------------


class LimitPagination(PaginationBase):
    limit_arg = 'limit'

    def __init__(self, default_limit=None, max_limit=None):
        self._default_limit = utils.if_none(default_limit, max_limit)
        self._max_limit = max_limit

        if self._max_limit is not None:
            assert \
                self._default_limit <= self._max_limit, \
                "default limit exceeds max limit"

    def get_page(self, query, view):
        limit = self.get_limit()
        if limit is not None:
            query = query.limit(limit + 1)

        items = query.all()

        if limit is not None and len(items) > limit:
            has_next_page = True
            items = items[:limit]
        else:
            has_next_page = False

        meta.set_response_meta(has_next_page=has_next_page)
        return items

    def get_limit(self):
        limit = flask.request.args.get(self.limit_arg)
        try:
            return self.parse_limit(limit)
        except ApiError as e:
            raise e.update({'source': {'parameter': self.limit_arg}})

    def parse_limit(self, limit):
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
        path['get'].add_parameter(name='limit',
                                  type='int',
                                  description='pagination limit')
        path['get'].add_property_to_response(
            prop_name='meta',
            type='object',
            properties={
                'has_next_page': {'type': 'boolean'}
            }
        )


class LimitOffsetPagination(LimitPagination):
    offset_arg = 'offset'

    def get_page(self, query, view):
        offset = self.get_offset()
        query = query.offset(offset)
        return super(LimitOffsetPagination, self).get_page(query, view)

    def get_offset(self):
        offset = flask.request.args.get(self.offset_arg)
        try:
            return self.parse_offset(offset)
        except ApiError as e:
            raise e.update({'source': {'parameter': self.offset_arg}})

    def parse_offset(self, offset):
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
            description='pagination offset')


class PagePagination(LimitOffsetPagination):
    page_arg = 'page'

    def __init__(self, page_size):
        super(PagePagination, self).__init__()
        self._page_size = page_size

    def get_offset(self):
        return self.get_request_page() * self._page_size

    def get_request_page(self):
        page = flask.request.args.get(self.page_arg)
        try:
            return self.parse_page(page)
        except ApiError as e:
            raise e.update({'source': {'parameter': self.page_arg}})

    def parse_page(self, page):
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
        return self._page_size

    def spec_declaration(self, path, spec, **kwargs):
        super(PagePagination, self).spec_declaration(path, spec)
        path['get'].add_parameter(
            name='page',
            type='int',
            description='page number')


# -----------------------------------------------------------------------------


class CursorPaginationBase(LimitPagination):
    cursor_arg = 'cursor'

    def get_column_orderings(self, query, view):
        column_orderings = tuple(
            self.get_column_ordering(expression)
            for expression in query._order_by
        )

        for id_field in view.id_fields:
            id_column = view.model.__table__.c[id_field]
            assert \
                id_column in (column for column, _ in column_orderings), \
                "ordering does not include {}".format(id_field)

        return column_orderings

    def get_column_ordering(self, expression):
        if isinstance(expression, Column):
            return expression, True

        column = expression.element
        assert isinstance(column, Column), "expression is not on a column"

        modifier = expression.modifier
        assert modifier in (sql.operators.asc_op, sql.operators.desc_op)
        asc = modifier == sql.operators.asc_op

        return column, asc

    def get_request_cursor(self, view, column_orderings):
        cursor = flask.request.args.get(self.cursor_arg)
        if not cursor:
            return None

        try:
            return self.parse_cursor(cursor, view, column_orderings)
        except ApiError as e:
            raise e.update({'source': {'parameter': self.cursor_arg}})

    def parse_cursor(self, cursor, view, column_orderings):
        cursor = self.decode_cursor(cursor)

        if len(cursor) != len(column_orderings):
            raise ApiError(400, {'code': 'invalid_cursor.length'})

        deserializer = view.deserializer
        column_fields = (
            deserializer.fields[column.name] for column, _ in column_orderings
        )

        try:
            cursor = tuple(
                field.deserialize(value)
                for field, value in zip(column_fields, cursor)
            )
        except ValidationError as e:
            errors = (
                self.format_validation_error(message)
                for message, path in utils.iter_validation_errors(e.messages)
            )
            raise ApiError(400, *errors)

        return cursor

    def decode_cursor(self, cursor):
        try:
            cursor = cursor.split('.')
            cursor = tuple(self.decode_value(value) for value in cursor)
        except (TypeError, ValueError):
            raise ApiError(400, {'code': 'invalid_cursor.encoding'})

        return cursor

    def decode_value(self, value):
        value = value.encode('ascii')
        value += (3 - ((len(value) + 3) % 4)) * b'='  # Add back padding.
        value = base64.urlsafe_b64decode(value)
        return value.decode()

    def format_validation_error(self, message):
        return {
            'code': 'invalid_cursor',
            'detail': message,
        }

    def get_filter(self, column_orderings, cursor):
        column_cursors = tuple(zip(column_orderings, cursor))
        return sa.or_(
            self.get_filter_clause(column_cursors[:i + 1])
            for i in range(len(column_cursors))
        )

    def get_filter_clause(self, column_cursors):
        previous_clauses = sa.and_(
            column == value for (column, _), value in column_cursors[:-1]
        )

        (column, asc), value = column_cursors[-1]
        if asc:
            current_clause = column > value
        else:
            current_clause = column < value

        return sa.and_(previous_clauses, current_clause)

    def make_cursors(self, items, view, column_orderings):
        column_fields = self.get_column_fields(view, column_orderings)
        return tuple(
            self.render_cursor(item, column_fields) for item in items
        )

    def make_cursor(self, item, view, column_orderings):
        column_fields = self.get_column_fields(view, column_orderings)
        return self.render_cursor(item, column_fields)

    def get_column_fields(self, view, column_orderings):
        serializer = view.serializer
        return tuple(
            serializer.fields[column.name] for column, _ in column_orderings
        )

    def render_cursor(self, item, column_fields):
        cursor = tuple(
            field._serialize(getattr(item, field.name), field.name, item)
            for field in column_fields
        )

        return self.encode_cursor(cursor)

    def encode_cursor(self, cursor):
        return '.'.join(self.encode_value(value) for value in cursor)

    def encode_value(self, value):
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
            description='pagination cursor')


class RelayCursorPagination(CursorPaginationBase):
    def get_page(self, query, view):
        column_orderings = self.get_column_orderings(query, view)

        cursor_in = self.get_request_cursor(view, column_orderings)
        if cursor_in is not None:
            query = query.filter(self.get_filter(column_orderings, cursor_in))

        items = super(RelayCursorPagination, self).get_page(query, view)

        # Relay expects a cursor for each item.
        cursors_out = self.make_cursors(items, view, column_orderings)
        meta.set_response_meta(cursors=cursors_out)

        return items

    def get_item_meta(self, item, view):
        query = view.get_list_query()
        column_orderings = self.get_column_orderings(query, view)

        cursor = self.make_cursor(item, view, column_orderings)
        return {'cursor': cursor}
