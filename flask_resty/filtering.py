import flask
from marshmallow import ValidationError
import sqlalchemy as sa

from .exceptions import ApiError
from . import utils

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
        except ValidationError as e:
            errors = (
                self.format_validation_error(message)
                for message, path in utils.iter_validation_errors(e.messages)
            )
            raise ApiError(400, *errors)

        return self.get_filter_clause(view, value)

    def format_validation_error(self, message):
        return {
            'code': 'invalid_filter',
            'detail': message,
        }

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
            arg_name: self.make_filter_field(arg_name, value)
            for arg_name, value in kwargs.items()
        }

    def make_filter_field(self, arg_name, value):
        if isinstance(value, FilterFieldBase):
            return value
        elif callable(value):
            return ColumnFilterField(arg_name, value)
        else:
            return ColumnFilterField(*value)

    def filter_query(self, query, view):
        for arg_name, filter_field in self._filter_fields.items():
            try:
                arg_value = flask.request.args[arg_name]
            except KeyError:
                continue

            try:
                query = query.filter(filter_field(view, arg_value))
            except ApiError as e:
                raise e.update({'source': {'parameter': arg_name}})

        return query

    def spec_declaration(self, path, spec, **kwargs):
        for arg_name, filter_field in self._filter_fields.items():
            path['get'].add_parameter(name=arg_name)
