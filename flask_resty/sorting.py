import flask

from .exceptions import ApiError

# -----------------------------------------------------------------------------


class SortingBase(object):
    """A declarative specification of how queries originating from a
    particular :py:class:`ModelView` should be sorted. Subclasses must
    implement :py:meth:`sort_query` to provide the sorting logic.
    """
    def sort_query(self, query, view):
        """Apply sorting criteria to the provided `query`.

        :param query: The query to sort.
        :type query: :py:class:`sqlalchemy.orm.query.Query`
        :param view: The view with the model we wish to sort.
        :type view: :py:class:`ModelView`
        :return: The sorted query
        :rtype: :py:class:`sqlalchemy.orm.query.Query`
        :raises: A :py:class:`NotImplementedError` if no implementation is
            provided.
        """
        raise NotImplementedError()


# -----------------------------------------------------------------------------


class FieldSortingBase(SortingBase):
    """A sorting specification that uses the fields on a particular
    :py:class:`ModelView`'s model to implement the sorting logic. Subclasses
    must implement :py:meth:`get_request_field_orderings` to specify how the
    sorting logic is parsed from the :py:class:`flask.Request`.
    """
    def sort_query(self, query, view):
        """Apply the sorting criteria from the :py:class:`flask.Request` to the
        provided `query`.

        :param query: The query to sort.
        :type query: :py:class:`sqlalchemy.orm.query.Query`
        :param view: The view with the model we wish to sort.
        :type view: :py:class:`ModelView`
        :return: The sorted query
        :rtype: :py:class:`sqlalchemy.orm.query.Query`
        """
        field_orderings = self.get_request_field_orderings(view)
        return self.sort_query_by_fields(query, view, field_orderings)

    def sort_query_by_fields(self, query, view, field_orderings):
        """Apply the sorting criteria to the provided `query`.

        :param query: The query to sort.
        :type query: :py:class:`sqlalchemy.orm.query.Query`
        :param view: The view with the model we wish to sort.
        :type view: :py:class:`ModelView`
        :param tuple field_orderings: A collection of field_orderings. See
            :py:meth:`get_criterion`.
        :return: The sorted query
        :rtype: :py:class:`sqlalchemy.orm.query.Query`
        """
        criteria = self.get_criteria(view, field_orderings)
        return query.order_by(*criteria)

    def get_request_field_orderings(self, view):
        """Generate a tuple of field orderings from the
        :py:class:`flask.Request`.

        :param view: The view with the model containing the target fields
        :type view: :py:class:`ModelView`
        :return: A sequence of field orderings. See :py:meth:`get_criterion`.
        :rtype: tuple
        :raises: A :py:class:`NotImplementedError` if no implementation is
            provided.
        """
        raise NotImplementedError()

    def get_field_orderings(self, fields):
        """Generate a tuple of field orderings for each field formatted in
        `fields`.

        :param fields: A collection of formatted fields, see
            :py:meth:`get_field_ordering`.
        :type fields: :py:class:`collection.abc.Sequence`
        :return: A sequence of field orderings. See :py:meth:`get_criterion`.
        :rtype: tuple
        """
        return tuple(
            self.get_field_ordering(field)
            for field in fields.split(','),
        )

    def get_field_ordering(self, field):
        """Generate a field ordering based on the formatting of the `field`.

        If the `field` begins with `-`, a descending field ordering will be
        returned. Otherwise, an ascending field ordering will be returned.

        :param str field: The formatted field.
        :return: A field ordering. See :py:meth:`get_criterion`.
        :rtype: tuple
        """
        if field and field[0] == '-':
            return field[1:], False

        return field, True

    def get_criteria(self, view, field_orderings):
        """Retrieve a tuple of sorting criterion for each column specified
        in `field_orderings`.

        :param view: The view with the model we wish to sort.
        :type view: :py:class:`ModelView`
        :return field_orderings: A collection of field_orderings. See
            :py:meth:`get_criterion`.
        :rtype: tuple
        """
        return tuple(
            self.get_criterion(view, field_ordering)
            for field_ordering in field_orderings,
        )

    def get_criterion(self, view, field_ordering):
        """Retrieve the sorting criterion for a column by using the
        `field_ordering` to apply the sorting logic to a particular field on
        the model attribute of the `view`.

        :param view: The view with the model we wish to sort.
        :type view: :py:class:`ModelView`
        :param field_ordering: The field ordering specification. The first
            position of the tuple represents the field_name. If the second
            position of the tuple is True, the field will be sorted in
            ascending order. If the second position of the tuple is False,
            the field will be sorted in descending order.
        :type field_ordering: A tuple (str, bool)
        :return: A column with sorting logic applied.
        :rtype: :py:class:`sqlalchemy.schema.Column`
        """
        field_name, asc = field_ordering
        column = self.get_column(view, field_name)
        return column if asc else column.desc()

    def get_column(self, view, field_name):
        """Retrieve a column by accessing the `field_name` on the model
        attribute of the `view`.

        :param view: The view with the model we wish to sort.
        :type view: :py:class:`ModelView`
        :param str field_name: The name of the column to retrieve.
        :return: The column we wish to sort.
        :rtype: :py:class:`sqlalchemy.schema.Column`
        """
        return getattr(view.model, field_name)


class FixedSorting(FieldSortingBase):
    """A sorting specification that uses the formatted `fields` to implement
    the sorting logic.

    For example, to sort queries by `name` ascending and `date` descending,
    specify the following in your :py:class:`ModelView`::

        sorting = FixedSorting('name,-date')

    :param str fields: The formatted fields.
    """
    def __init__(self, fields):
        self._field_orderings = self.get_field_orderings(fields)

    def get_request_field_orderings(self, view):
        """Ignores the request and uses the fields provided in the constructor
        to specify the field orderings.

        :param view: The view with the model we wish to sort.
        :type view: :py:class:`ModelView`
        :return field_orderings: A collection of field_orderings. See
            :py:meth:`get_criterion`.
        :rtype: tuple
        """
        return self._field_orderings


class Sorting(FieldSortingBase):
    """A sorting specification that uses the formatted `field_names` and the
    request parameter specified in `sort_arg` to implement the sorting logic.

    For example, to sort `name` and `date` based on the `sort_arg` request
    parameter, specify the following in your :py:class:`ModelView`::

        sorting = Sorting('name', 'date')

    One or both of `name` or `date` can be formatted in the `sort_arg` request
    parameter to determine the sort order.

    :param str field_names: The fields available for sorting.
    :param str default: If provided, specifies a default sort order in the
        case that the `sort_arg` is not provided in the request.
    """

    #: The request parameter from which the formatted sorting fields will be
    #: retrieved.
    sort_arg = 'sort'

    def __init__(self, *field_names, **kwargs):
        self._field_names = frozenset(field_names)
        self._default_sort = kwargs.get('default')

    def get_request_field_orderings(self, view):
        """Retrieves the field orderings from the
        :py:attr:`flask.Request.args`. If the :py:attr:`sort_arg` is not
        provided, an empty tuple will be returned.

        :param view: The view with the model we wish to sort.
        :type view: :py:class:`ModelView`
        :return field_orderings: A collection of field_orderings. See
            :py:meth:`get_criterion`.
        :rtype: tuple
        :raises: An HTTP 400 :py:class:`ApiError` if a field name is provided
            in the request that does not exist in the provided sequence of
            field_names.
        """
        sort = flask.request.args.get(self.sort_arg, self._default_sort)
        if sort is None:
            return ()

        field_orderings = self.get_field_orderings(sort)
        for field_name, _ in field_orderings:
            if field_name not in self._field_names:
                raise ApiError(400, {
                    'code': 'invalid_sort',
                    'source': {'parameter': self.sort_arg},
                })

        return field_orderings

    def spec_declaration(self, path, spec, **kwargs):
        path['get'].add_parameter(
            name='sort',
            type='string',
            description="field to sort by",
        )
