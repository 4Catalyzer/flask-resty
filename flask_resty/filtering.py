import copy
import flask
import functools
import marshmallow
import sqlalchemy as sa
from marshmallow import ValidationError
from sqlalchemy import sql

from .exceptions import ApiError

# -----------------------------------------------------------------------------


class ArgFilterBase:
    """An abstract specification of a filter from a query argument.

    Implementing classes must provide :py:meth:`maybe_set_arg_name` and
    :py:meth:`filter_query`.
    """

    def maybe_set_arg_name(self, arg_name):
        """Set the name of the argument to which this filter is bound.

        :param str arg_name: The name of the field to filter against.
        :raises: :py:class:`NotImplementedError` if no implementation is
            provided.
        """
        raise NotImplementedError()

    def filter_query(self, query, view, arg_value):
        """Filter the query.

        :param query: The query to filter.
        :type query: :py:class:`sqlalchemy.orm.query.Query`
        :param view: The view with the model we wish to filter for.
        :type view: :py:class:`ModelView`
        :param str arg_value: The filter specification
        :return: The filtered query
        :rtype: :py:class:`sqlalchemy.orm.query.Query`
        :raises: :py:class:`NotImplementedError` if no implementation is
            provided.
        """
        raise NotImplementedError()


# -----------------------------------------------------------------------------


class FieldFilterBase(ArgFilterBase):
    """A filter that uses a marshmallow field to deserialize its value.

    Implementing classes must provide :py:meth:`get_filter_field` and
    :py:meth:`get_filter_clause`.

    :param str separator: Character that separates individual elements in the
        query value.
    :param bool allow_empty: If set, allow filtering for empty values;
        otherwise, filter out all items on an empty value.
    :param bool skip_invalid: If set, ignore invalid filter values instead of
        throwing an API error.
    """

    def __init__(
        self, *, separator=",", allow_empty=False, skip_invalid=False
    ):
        self._separator = separator
        self._allow_empty = allow_empty
        self._skip_invalid = skip_invalid

    def maybe_set_arg_name(self, arg_name):
        pass

    def filter_query(self, query, view, arg_value):
        filter = self.get_filter(view, arg_value)
        if filter is None:
            return query

        return query.filter(filter)

    def get_filter(self, view, arg_value):
        if arg_value is None:
            return self.get_default_filter(view)

        if not arg_value and not self._allow_empty:
            return sql.false()

        if not self._separator or self._separator not in arg_value:
            return self.get_element_filter(view, arg_value)

        return sa.or_(
            self.get_element_filter(view, value_raw)
            for value_raw in arg_value.split(self._separator)
        )

    def get_default_filter(self, view):
        field = self.get_field(view)
        if field.required:
            raise ApiError(400, {"code": "invalid_filter.missing"})

        value = field.missing() if callable(field.missing) else field.missing
        if value is marshmallow.missing:
            return None

        return self.get_element_filter(view, value)

    def get_element_filter(self, view, value):
        field = self.get_field(view)

        try:
            value = self.deserialize(field, value)
        except ValidationError as e:
            if self._skip_invalid:
                return sql.false()

            raise ApiError.from_validation_error(
                400, e, self.format_validation_error
            ) from e

        return self.get_filter_clause(view, value)

    def deserialize(self, field, value_raw):
        """Overridable hook for deserializing a value.

        :param field: The marshmallow field.
        :type field: :py:class:`marshmallow.fields.Field`
        :param value_raw: The value to deserialize.
        :return: The deserialized value.
        """
        return field.deserialize(value_raw)

    def format_validation_error(self, message, path):
        return {"code": "invalid_filter", "detail": message}

    def get_field(self, view):
        """Get the marshmallow field for deserializing filter values.

        :param view: The view with the model we wish to filter for.
        :type view: :py:class:`ModelView`
        :raises: :py:class:`NotImplementedError` if no implementation is
            provided.
        """
        raise NotImplementedError()

    def get_filter_clause(self, view, value):
        """Build the filter clause for the deserialized value.

        :param view: The view with the model we wish to filter for.
        :type view: :py:class:`ModelView`
        :param str value: The right-hand side of the WHERE clause.
        :raises: :py:class:`NotImplementedError` if no implementation is
            provided.
        """
        raise NotImplementedError()


class ColumnFilter(FieldFilterBase):
    """A filter that operates on the value of a database column.

    This filter relies on the schema to deserialize the query argument values.
    `ColumnFilter` cannot normally be used for columns that do not appear on
    the schema, but such columns can be added to the schema with fields that
    have both `load_only` and `dump_only` set.

    :param str column_name: The name of the column to filter against.
    :param func operator: A callable that returns the filter expression given
        the column and the filter value.
    :param bool required: If set, fail if this filter is not specified.
    :param bool validate: If unset, bypass validation on the field. This is
        useful if the field specifies validation rule for inputs that are not
        relevant for filters.
    """

    def __init__(
        self,
        column_name=None,
        operator=None,
        *,
        required=False,
        missing=marshmallow.missing,
        validate=True,
        **kwargs,
    ):
        super().__init__(**kwargs)

        if operator is None and callable(column_name):
            operator = column_name
            column_name = None

        if not operator:
            raise TypeError("must specify operator")

        self._has_explicit_column_name = column_name is not None
        self._column_name = column_name

        self._operator = operator

        self._fields = {}
        self._required = required
        self._missing = missing

        self._validate = validate

    def maybe_set_arg_name(self, arg_name):
        """Set `arg_name` as the column name if no explicit value is available.

        :param str arg_name: The name of the column to filter against.
        """
        if self._has_explicit_column_name:
            return

        if self._column_name and self._column_name != arg_name:
            raise TypeError(
                "cannot use ColumnFilter without explicit column name for multiple arg names"
            )

        self._column_name = arg_name

    def get_field(self, view):
        """Construct the marshmallow field for deserializing filter values.

        This takes the field from the deserializer, then creates a copy with
        the desired semantics around missing values.

        :param view: The view with the model we wish to filter for.
        :type view: :py:class:`ModelView`
        """
        base_field = view.deserializer.fields[self._column_name]

        try:
            field = self._fields[base_field]
        except KeyError:
            # We don't want the default value handling on the original field,
            # as that's only relevant for object deserialization.
            field = copy.deepcopy(base_field)
            field.required = self._required
            field.missing = self._missing

            self._fields[base_field] = field

        return field

    def get_filter_clause(self, view, value):
        column = getattr(view.model, self._column_name)
        return self._operator(column, value)

    def deserialize(self, field, value_raw):
        """Deserialize `value_raw`, optionally skipping validation.

        :param field: The marshmallow field.
        :type field: :py:class:`marshmallow.fields.Field`
        :param value_raw: The value to deserialize.
        :return: The deserialized value.
        """
        if not self._validate:
            # We may not want to apply the same validation for filters as we do
            #  on model fields. This bypasses the irrelevant handling of
            #  missing and None values, and skips the validation check.
            return field._deserialize(value_raw, None, None)

        return super().deserialize(field, value_raw)


class ModelFilter(FieldFilterBase):
    """An arbitrary filter against the model.

    :param field: A marshmallow field for deserializing filter values.
    :type field: :py:class:`marshmallow.fields.Field`
    :param filter: A callable that returns the filter expression given the
        model and the filter value.
    :param dict kwargs: Passed to :py:class:`FieldFilterBase`.
    """

    def __init__(self, field, filter, **kwargs):
        super().__init__(**kwargs)

        self._field = field
        self._filter = filter

    def get_field(self, view):
        return self._field

    def get_filter_clause(self, view, value):
        return self._filter(view.model, value)


# -----------------------------------------------------------------------------


def model_filter(field, **kwargs):
    """A convenience decorator for building a `ModelFilter`.

    This decorator allows building a `ModelFilter` around a named function::

        @model_filter(fields.String(required=True))
        def filter_color(model, value):
            return model.color == value

    :param field: A marshmallow field for deserializing filter values.
    :type field: :py:class:`marshmallow.fields.Field`
    :param dict kwargs: Passed to :py:class:`ModelFilter`.
    """

    def wrapper(func):
        filter_field = ModelFilter(field, func, **kwargs)
        functools.update_wrapper(filter_field, func)
        return filter_field

    return wrapper


# -----------------------------------------------------------------------------


class Filtering:
    """Container for the arg filters on a :py:class:`ModelView`.

    :param dict kwargs: A mapping from filter field names to filters.
    """

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
        """Filter a query using the configured filters and the request args.

        :param query: The query to filter.
        :type query: :py:class:`sqlalchemy.orm.query.Query`
        :param view: The view with the model we wish to filter for.
        :type view: :py:class:`ModelView`
        :return: The filtered query
        :rtype: :py:class:`sqlalchemy.orm.query.Query`
        """
        args = flask.request.args

        for arg_name, arg_filter in self._arg_filters.items():
            try:
                arg_value = args[arg_name]
            except KeyError:
                arg_value = None

            try:
                query = arg_filter.filter_query(query, view, arg_value)
            except ApiError as e:
                raise e.update({"source": {"parameter": arg_name}})

        return query

    def __or__(self, other):
        """Combine two `Filtering` instances.

        `Filtering` supports view inheritance by implementing the `|` operator.
        For example, `Filtering(foo=..., bar=...) | Filtering(baz=...)` will
        create a new `Filtering` instance with filters for each `foo`, `bar`
        and `baz`. Filters on the right-hand side take precedence where each
        `Filtering` instance has the same key.
        """
        if not isinstance(other, Filtering):
            return NotImplemented

        return self.__class__(**{**self._arg_filters, **other._arg_filters})
