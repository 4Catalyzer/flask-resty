import functools

import flask
from marshmallow import missing, ValidationError
import sqlalchemy as sa
from sqlalchemy import sql

from .exceptions import ApiError
from .utils import iter_validation_errors

# -----------------------------------------------------------------------------


class ArgFilterBase(object):
    def maybe_set_arg_name(self, arg_name):
        raise NotImplementedError()

    def filter_query(self, query, view, arg_value):
        raise NotImplementedError()


# -----------------------------------------------------------------------------


class FieldFilterBase(ArgFilterBase):
    def __init__(self, separator=',', allow_empty=False, skip_invalid=False):
        self._separator = separator
        self._allow_empty = allow_empty
        self._skip_invalid = skip_invalid

    def maybe_set_arg_name(self, arg_name):
        pass

    def filter_query(self, query, view, arg_value):
        return query.filter(self.get_filter(view, arg_value))

    def get_filter(self, view, arg_value):
        if arg_value is None:
            return self.get_element_filter(view, missing)

        if not arg_value and not self._allow_empty:
            return sql.false()

        if not self._separator or self._separator not in arg_value:
            return self.get_element_filter(view, arg_value)

        return sa.or_(
            self.get_element_filter(view, value_raw)
            for value_raw in arg_value.split(self._separator)
        )

    def get_element_filter(self, view, value_raw):
        field = self.get_field(view)
        if value_raw is missing and not field.required:
            return sql.true()

        try:
            value = self.deserialize(field, value_raw)
        except ValidationError as e:
            if self._skip_invalid:
                return sql.false()

            raise ApiError(400, *(
                self.format_validation_error(message)
                for message, path in iter_validation_errors(e.messages)
            ))

        return self.get_filter_clause(view, value)

    def deserialize(self, field, value_raw):
        return field.deserialize(value_raw)

    def format_validation_error(self, message):
        return {
            'code': 'invalid_filter',
            'detail': message,
        }

    def get_field(self, view):
        raise NotImplementedError()

    def get_filter_clause(self, view, value):
        raise NotImplementedError()


class ColumnFilter(FieldFilterBase):
    def __init__(
        self,
        column_name=None,
        operator=None,
        required=False,
        validate=True,
        **kwargs
    ):
        super(ColumnFilter, self).__init__(**kwargs)

        if operator is None and callable(column_name):
            operator = column_name
            column_name = None

        if not operator:
            raise TypeError("must specify operator")

        self._has_explicit_column_name = column_name is not None
        self._column_name = column_name
        self._operator = operator
        self._required = required
        self._validate = validate

    def maybe_set_arg_name(self, arg_name):
        if self._has_explicit_column_name:
            return

        if self._column_name and self._column_name != arg_name:
            raise TypeError(
                "cannot use ColumnFilter without explicit column name " +
                "for multiple arg names",
            )

        self._column_name = arg_name

    def filter_query(self, query, view, arg_value):
        # Missing value handling on the schema field is not relevant here.
        if arg_value is None:
            if not self._required:
                return query

            raise ApiError(400, {'code': 'invalid_filter.missing'})

        return super(ColumnFilter, self).filter_query(query, view, arg_value)

    def get_field(self, view):
        return view.deserializer.fields[self._column_name]

    def get_filter_clause(self, view, value):
        column = getattr(view.model, self._column_name)
        return self._operator(column, value)

    def deserialize(self, field, value_raw):
        if not self._validate:
            # We may not want to apply the same validation for filters as we do
            # on model fields. This bypasses the irrelevant handling of missing
            # and None values, and skips the validation check.
            return field._deserialize(value_raw, None, None)

        return super(ColumnFilter, self).deserialize(field, value_raw)


class ModelFilter(FieldFilterBase):
    def __init__(self, field, filter, **kwargs):
        super(ModelFilter, self).__init__(**kwargs)

        self._field = field
        self._filter = filter

    def get_field(self, view):
        return self._field

    def get_filter_clause(self, view, value):
        return self._filter(view.model, value)


# -----------------------------------------------------------------------------


def model_filter(field, **kwargs):
    def wrapper(func):
        filter_field = ModelFilter(field, func, **kwargs)
        functools.update_wrapper(filter_field, func)
        return filter_field

    return wrapper


# -----------------------------------------------------------------------------


class Filtering(object):
    def __init__(self, **kwargs):
        self._arg_filters = {
            arg_name: self.make_arg_filter(arg_name, arg_filter)
            for arg_name, arg_filter in kwargs.items()
        }

    def make_arg_filter(self, arg_name, arg_filter):
        if callable(arg_filter):
            arg_filter = ColumnFilter(arg_name, arg_filter)

        arg_filter.maybe_set_arg_name(arg_name)

        return arg_filter

    def filter_query(self, query, view):
        args = flask.request.args

        for arg_name, arg_filter in self._arg_filters.items():
            try:
                arg_value = args[arg_name]
            except KeyError:
                arg_value = None

            try:
                query = arg_filter.filter_query(query, view, arg_value)
            except ApiError as e:
                raise e.update({'source': {'parameter': arg_name}})

        return query

    def spec_declaration(self, path, spec, **kwargs):
        for arg_name in self._arg_filters:
            path['get'].add_parameter(name=arg_name)
