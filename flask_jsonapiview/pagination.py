import base64
import flask
import json
import logging
from marshmallow import ValidationError
import sqlalchemy as sa
from sqlalchemy import Column, sql

from . import meta
from . import utils

__all__ = ('IdCursorPagination',)

# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------


class IdCursorPagination(object):
    def __init__(self, default_limit=None, max_limit=None):
        self._default_limit = utils.if_none(default_limit, max_limit)
        self._max_limit = max_limit

    def __call__(self, query, api):
        column_specs = self.get_column_specs(query, api)

        cursor = self.load_cursor(api, column_specs)
        if cursor is not None:
            query = query.filter(self.get_filter(column_specs, cursor))

        limit = self.get_limit()
        if limit is not None:
            query = query.limit(limit + 1)

        collection = query.all()

        if limit is not None and len(collection) > limit:
            has_more = True
            collection = collection[:limit]
        else:
            has_more = False

        dumped_cursors = self.dump_cursors(api, column_specs, collection)

        meta.set_response_meta({'has-more': has_more}, cursors=dumped_cursors)
        return collection

    def get_column_specs(self, query, api):
        column_specs = tuple(
            self.get_column_spec(expression) for expression in query._order_by
        )

        id_column = api.model.__table__.c.id
        assert \
            id_column in (column for column, _ in column_specs), \
            "ordering does not include id"

        return column_specs

    def get_column_spec(self, expression):
        if isinstance(expression, Column):
            return expression, True

        column = expression.element
        assert isinstance(column, Column), "expression is not on a column"

        modifier = expression.modifier
        if modifier == sql.operators.asc_op:
            asc = True
        elif modifier == sql.operators.desc_op:
            asc = False
        else:
            assert False, "unrecognized expression modifier"

        return column, asc

    def load_cursor(self, api, column_specs):
        cursor = flask.request.args.get('page[cursor]', None)
        if not cursor:
            return None

        cursor = self.decode_cursor(cursor)

        if len(cursor) != len(column_specs):
            logger.warning(
                "incorrect cursor field count, got {} but expected {}"
                .format(len(cursor), len(column_specs))
            )
            flask.abort(400)

        deserializer = api.deserializer
        column_fields = (
            deserializer.fields[column.name] for column, _ in column_specs
        )

        try:
            cursor = tuple(
                field.deserialize(value)
                for field, value in zip(column_fields, cursor)
            )
        except ValidationError:
            logger.warning("invalid cursor", exc_info=True)
            flask.abort(400)

        return cursor

    def decode_cursor(self, cursor):
        try:
            cursor = cursor.encode('ascii')
            cursor = base64.urlsafe_b64decode(cursor)
            cursor = cursor.decode('utf-8')
            cursor = json.loads(cursor)
        except (TypeError, ValueError):
            logger.warning("incorrectly encoded cursor", exc_info=True)
            flask.abort(400)

        return cursor

    def get_filter(self, column_specs, cursor):
        filter_specs = zip(column_specs, cursor)
        return sa.or_(
            self.get_filter_clause(filter_specs[:i + 1])
            for i in range(len(filter_specs))
        )

    def get_filter_clause(self, filter_specs):
        previous_clauses = sa.and_(
            column == value for (column, _), value in filter_specs[:-1]
        )

        (column, asc), value = filter_specs[-1]
        if asc:
            current_clause = column > value
        else:
            current_clause = column < value

        return sa.and_(previous_clauses, current_clause)

    def get_limit(self):
        limit = flask.request.args.get('page[limit]', None)
        if not limit:
            return self._default_limit

        try:
            limit = int(limit)
        except ValueError:
            logger.warning("invalid limit", exc_info=True)
            flask.abort(400)

        if limit < 0:
            logging.warning("limit must be non-negative, got {}".format(limit))
            flask.abort(400)

        if self._max_limit is not None:
            limit = min(limit, self._max_limit)

        return limit

    def dump_cursors(self, api, column_specs, collection):
        serializer = api.serializer
        column_fields = tuple(
            serializer.fields[column.name] for column, _ in column_specs
        )

        return tuple(
            self.dump_cursor(item, column_fields) for item in collection
        )

    def dump_cursor(self, item, column_fields):
        cursor = tuple(
            field._serialize(getattr(item, field.name), field.name, item)
            for field in column_fields
        )

        return self.encode_cursor(cursor)

    def encode_cursor(self, cursor):
        cursor = json.dumps(cursor)
        cursor = cursor.encode('utf-8')
        cursor = base64.urlsafe_b64encode(cursor)
        return cursor.decode('ascii')
