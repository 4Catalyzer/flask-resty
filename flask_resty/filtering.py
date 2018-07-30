import functools

import flask
from marshmallow import missing, ValidationError
import sqlalchemy as sa
from sqlalchemy import sql

from .exceptions import ApiError
from .utils import iter_validation_errors

# -----------------------------------------------------------------------------


class ArgFilterBase(object):
    """An abstract specification of a filter.

    Implementing classes must provide :py:meth:`maybe_set_arg_name` and
    :py:meth:`filter_query`.
    """

    def maybe_set_arg_name(self, arg_name):
        """Store the `arg_name` as a field to filter against, if appropriate.

        :param str arg_name: The name of the field to filter against.
        :raises: :py:class:`NotImplementedError` if no implementation is
            provided.
        """
        raise NotImplementedError()

    def filter_query(self, query, view, arg_value):
        """Applies a WHERE clause to the `query`.

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
    """A facility for constructing queries against an arbitrary collection.

    Implementing classes must provide :py:meth:`get_filter_field` and 
    :py:meth:`get_filter_clause`.

    :param str separator: Glyph that separates filter fields in the filter
        specification.
    :param bool allow_empty: If True, NULL values can be used as a filter clause.
    :param bool skip_invalid: If True, invalid filter values should NOT raise
        an exception.
    """

    def __init__(self, separator=',', allow_empty=False, skip_invalid=False):
        self._separator = separator
        self._allow_empty = allow_empty
        self._skip_invalid = skip_invalid

    def maybe_set_arg_name(self, arg_name):
        """FIXME: Does this need to be here?"""
        pass

    def filter_query(self, query, view, arg_value):
        """Applies a WHERE clause to the `query` from the result of calling
        :py:meth:`get_filter` on the provided `view` and `arg_value`.

        :param query: The query to filter.
        :type query: :py:class:`sqlalchemy.orm.query.Query`
        :param view: The view with the model we wish to filter for.
        :type view: :py:class:`ModelView`
        :param str arg_value: The filter specification
        :return: The filtered query
        :rtype: :py:class:`sqlalchemy.orm.query.Query`
        """
        return query.filter(self.get_filter(view, arg_value))

    def get_filter(self, view, arg_value):
        """Retrieve a filter clause consisting of the disjunction of each
        filter constructed from calling :py:meth:`get_element_filter` on each
        element in `arg_value`.

        :param view: The view with the model we wish to filter for.
        :type view: :py:class:`ModelView`
        :param str arg_value: The filter specification
        :return: The filter clause
        """
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
        """Retrieve a filter clause against the field corresponding to the
        element in `value_raw`.

        :param view: The view with the model we wish to filter for.
        :type view: :py:class:`ModelView`
        :param str value_raw: The value corresponding to the right-hand side
            of the WHERE clause.
        :return: The filter clause
        """
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
        """Deserialize `value_raw` by calling deserialize on `field`.

        :param str field: The Marshmallow field.
        :param value_raw: The value to deserialize.
        :return: The deserialized value.
        """
        return field.deserialize(value_raw)

    def format_validation_error(self, message):
        """Create a dictionary that describes the validation error provided in
        `message`. The response body has the following structure::

            code:
                type: string
                description: Always the literal `invalid_filter`
            detail:
                type: string
                description: The message in `message`

        :return: The formatted validation error
        :rtype: dict
        """
        return {
            'code': 'invalid_filter',
            'detail': message,
        }

    def get_field(self, view):
        """Retreives the target field for filtering.

        :param view: The view with the model we wish to filter for.
        :type view: :py:class:`ModelView`
        :raises: :py:class:`NotImplementedError` if no implementation is
            provided.
        """
        raise NotImplementedError()

    def get_filter_clause(self, view, value):
        """Retrieves a filter clause against the provided `value`.

        :param view: The view with the model we wish to filter for.
        :type view: :py:class:`ModelView`
        :param str value: The right-hand side of the WHERE clause.
        :raises: :py:class:`NotImplementedError` if no implementation is
            provided.
        """
        raise NotImplementedError()


class ColumnFilter(FieldFilterBase):
    """A facility for constructing queries against a database column.

    :param str column_name: The name of the column to filter against.
    :param func operator: A callable that maps to a SQL operator.
    :param bool required: If True, an exception will be raised if a value
        for the filter is not provided in the request args.
    :param bool validate: If True, an exception will be raised if the value
        for the filter cannot be deserialized.
    """

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
        """If no column name is set, store the given `arg_name` as the column
        name.

        :param str arg_name: The name of the column to filter against.
        """
        if self._has_explicit_column_name:
            return

        if self._column_name and self._column_name != arg_name:
            raise TypeError(
                "cannot use ColumnFilter without explicit column name " +
                "for multiple arg names",
            )

        self._column_name = arg_name

    def filter_query(self, query, view, arg_value):
        """Ensures that required filters are present before calling
        :py:meth:`FieldFilterBase.filter_query`.

        :param query: The query to filter.
        :type query: :py:class:`sqlalchemy.orm.query.Query`
        :param view: The view with the model we wish to filter for.
        :type view: :py:class:`ModelView`
        :param str arg_value: The filter specification
        :return: The filtered query
        :rtype: :py:class:`sqlalchemy.orm.query.Query`
        :raises: :py:class:`ApiError` if the filter is required and the
            `arg_value` is None.
        """
        # Missing value handling on the schema field is not relevant here.
        if arg_value is None:
            if not self._required:
                return query

            raise ApiError(400, {'code': 'invalid_filter.missing'})

        return super(ColumnFilter, self).filter_query(query, view, arg_value)

    def get_field(self, view):
        """Retreives the target field for filtering by inspecting
        :py:attr:`ModelView.deserializer` on the provided `view`.

        :param view: The view with the model we wish to filter for.
        :type view: :py:class:`ModelView`
        """
        return view.deserializer.fields[self._column_name]

    def get_filter_clause(self, view, value):
        """Retrieves a filter clause for the stored column against the
        provided `value`.

        :param view: The view with the model we wish to filter for.
        :type view: :py:class:`ModelView`
        :param str value: The right-hand side of the WHERE clause.
        """
        column = getattr(view.model, self._column_name)
        return self._operator(column, value)

    def deserialize(self, field, value_raw):
        """Deserialize `value_raw`, skipping validation if we do not want it.

        :param str field: The Marshmallow field.
        :param value_raw: The value to deserialize.
        :return: The deserialized value.
        """
        if not self._validate:
            # We may not want to apply the same validation for filters as we do
            # on model fields. This bypasses the irrelevant handling of missing
            # and None values, and skips the validation check.
            return field._deserialize(value_raw, None, None)

        return super(ColumnFilter, self).deserialize(field, value_raw)


class ModelFilter(FieldFilterBase):
    """A facility for constructing filtered queries against a
    :py:class:`ModelView`.

    :param str field: The field to filter against.
    :param filter: The filtering routine, defaults to :py:func:`filter`.
    :param dict kwargs: Passed to :py:class:`FieldFilterBase`.
    """

    def __init__(self, field, filter, **kwargs):
        super(ModelFilter, self).__init__(**kwargs)

        self._field = field
        self._filter = filter

    def get_field(self, view):
        """Retrieves the stored filter field.

        :return: The stored filter field.
        :rtype: str
        """
        return self._field

    def get_filter_clause(self, view, value):
        """Applies the stored filtering routine to the
        :py:attr:`ModelView.model` and the given `value`.

        :param view: The view with the model we wish to filter for.
        :type view: :py:class:`ModelView`
        :param str value: The right-hand side of the WHERE clause.
        :return: The filter clause.
        """
        return self._filter(view.model, value)


# -----------------------------------------------------------------------------


def model_filter(field, **kwargs):
    """A decorator interface for :py:class:`ModelFilter`. FIXME: example

    :param str field: The field to filter against.
    :param dict kwargs: Passed to :py:class:`ModelFilter`.
    """
    def wrapper(func):
        filter_field = ModelFilter(field, func, **kwargs)
        functools.update_wrapper(filter_field, func)
        return filter_field

    return wrapper


# -----------------------------------------------------------------------------


class Filtering(object):
    """A facility for constructing WHERE clauses in queries against a
    particular :py:class:`ModelView`.

    :param dict kwargs: A mapping from filter field names to filter
        specifications. 
    """

    def __init__(self, **kwargs):
        self._arg_filters = {
            arg_name: self.make_arg_filter(arg_name, arg_filter)
            for arg_name, arg_filter in kwargs.items()
        }

    def make_arg_filter(self, arg_name, arg_filter):
        """Construct a class inheriting from :py:class:`ArgFilterBase` that
        filters against the field corresponding to `arg_name`.

        :param str arg_name: The field to filter against.
        :param arg_filter: Either a callable operator or a class inheriting
            from :py:class:`ArgFilterBase`.
        :return: A class inheriting from :py:class:`ArgFilterBase`.
        """
        if callable(arg_filter):
            arg_filter = ColumnFilter(arg_name, arg_filter)

        arg_filter.maybe_set_arg_name(arg_name)

        return arg_filter

    def filter_query(self, query, view):
        """Applies a WHERE clause to `query` using the filter args from
        :py:attr:`flask.Request.args`.

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
                raise e.update({'source': {'parameter': arg_name}})

        return query

    def spec_declaration(self, path, spec, **kwargs):
        for arg_name in self._arg_filters:
            path['get'].add_parameter(name=arg_name)
