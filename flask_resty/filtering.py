import flask
import logging
from marshmallow import ValidationError
import sqlalchemy as sa

# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------


class FilterFieldBase(object):
    def __init__(self, separator=','):
        self._separator = separator

    def __call__(self, view, arg_value):
        if not self._separator or self._separator not in arg_value:
            return self.get_arg_clause(view, arg_value)

        return sa.or_(
            self.get_arg_clause(view, value)
            for value in arg_value.split(self._separator)
        )

    def get_arg_clause(self, view, arg_value):
        field = self.get_field(view)
        try:
            value = field.deserialize(arg_value)
        except ValidationError:
            logger.warning("invalid filter value", exc_info=True)
            flask.abort(400)
        else:
            return self.get_filter_clause(view, value)

    def get_field(self, view):
        raise NotImplementedError()

    def get_filter_clause(self, view, value):
        raise NotImplementedError()


class ColumnFilterField(FilterFieldBase):
    def __init__(self, column_name, operator, **kwargs):
        super(ColumnFilterField, self).__init__(**kwargs)
        self._column_name = column_name
        self._operator = operator

    def get_field(self, view):
        return view.deserializer.fields[self._column_name]

    def get_filter_clause(self, view, value):
        column = getattr(view.model, self._column_name)
        return self._operator(column, value)


class ModelFilterField(FilterFieldBase):
    def __init__(self, field, filter, **kwargs):
        super(ModelFilterField, self).__init__(**kwargs)
        self._field = field
        self._filter = filter

    def get_field(self, view):
        return self._field

    def get_filter_clause(self, view, value):
        return self._filter(view.model, value)


# -----------------------------------------------------------------------------


class Filtering(object):
    def __init__(self, **kwargs):
        self._filter_fields = {
            key: self.get_filter_field(key, value)
            for key, value in kwargs.items()
        }

    def get_filter_field(self, key, value):
        if isinstance(value, FilterFieldBase):
            return value
        elif callable(value):
            return ColumnFilterField(key, value)
        else:
            return ColumnFilterField(*value)

    def __call__(self, query, view):
        for key, filter_field in self._filter_fields.items():
            try:
                arg_value = flask.request.args[key]
            except KeyError:
                continue

            query = query.filter(filter_field(view, arg_value))

        return query
