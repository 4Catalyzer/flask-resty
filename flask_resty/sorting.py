import flask
import sqlalchemy as sa

from .exceptions import ApiError

# -----------------------------------------------------------------------------


class SortingBase:
    """The base class for sorting components.

    Sorting components control how list queries are sorted.

    They also expose an API for cursor pagination components to get the sort
    fields, which are required to build cursors.

    Subclasses must implement :py:meth:`sort_query` to provide the sorting
    logic.
    """

    def sort_query(self, query, view):
        """Sort the provided `query`.

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
    """The base class for sorting components that sort on model fields.

    These sorting components work on JSON-API style sort field strings, which
    consist of a list of comma-separated field names, optionally prepended by
    ``-`` to indicate descending sort order.

    For example, the sort field string of ``name,-date`` will sort by `name`
    ascending and `date` descending.

    Subclasses must implement :py:meth:`get_request_field_orderings` to specify
    the actual field orderings to use.
    """

    def sort_query(self, query, view):
        field_orderings = self.get_request_field_orderings(view)
        return self.sort_query_by_fields(query, view, field_orderings)

    def sort_query_by_fields(self, query, view, field_orderings):
        criteria = self.get_criteria(view, field_orderings)
        return query.order_by(*criteria)

    def get_request_field_orderings(self, view):
        """Get the field orderings to use for the current request.

        These should be created from a sort field string with
        `get_field_orderings` below.

        :param view: The view with the model containing the target fields
        :type view: :py:class:`ModelView`
        :return: A sequence of field orderings. See :py:meth:`get_criterion`.
        :rtype: tuple
        :raises: A :py:class:`NotImplementedError` if no implementation is
            provided.
        """
        raise NotImplementedError()

    def get_field_orderings(self, fields):
        """Given a sort field string, build the field orderings.

        These field orders can then be used with `get_request_field_orderings`
        above. See the class documentation for details on sort field strings.

        :param str fields: The sort field string.
        :return: A sequence of field orderings. See :py:meth:`get_criterion`.
        :rtype: tuple
        """
        return tuple(
            self.get_field_ordering(field) for field in fields.split(",")
        )

    def get_field_ordering(self, field):
        if field and field[0] == "-":
            return field[1:], False

        return field, True

    def get_criteria(self, view, field_orderings):
        return tuple(
            self.get_criterion(view, field_ordering)
            for field_ordering in field_orderings
        )

    def get_criterion(self, view, field_ordering):
        field_name, asc = field_ordering
        column = self.get_column(view, field_name)
        return column if asc else column.desc()

    def get_column(self, view, field_name):
        return getattr(view.model, field_name)


class FixedSorting(FieldSortingBase):
    """A sorting component that applies a fixed sort order.

    For example, to sort queries by `name` ascending and `date` descending,
    specify the following in your view::

        sorting = FixedSorting('name,-date')

    :param str fields: The formatted fields.
    """

    def __init__(self, fields):
        self._field_orderings = self.get_field_orderings(fields)

    def get_request_field_orderings(self, view):
        return self._field_orderings


class Sorting(FieldSortingBase):
    """A sorting component that allows the user to specify sort fields.

    For example, to allow users to sort by `title` and/or `content_length`,
    specify the following in your view::

        sorting = Sorting(
            'title',
            content_length=sql.func.length(Post.content)
        )

    One or both of `title` or `content_length` can be formatted in the
    `sort_arg` request parameter to determine the sort order. For example,
    users can sort requests by `name` ascending and `date` descending by
    making a ``GET`` request to::

        /api/comments/?sort=title,-content_length

    :param str field_names: The fields available for sorting.
        Names should match a column on your View's ``model``.
    :param str default: If provided, specifies a default sort order when the
        request does not specify an explicit sort order.
    :param dict kwargs: Provide custom sort behavior by mapping a sort
        argument name to a model order_by expression.
    """

    #: The request parameter from which the formatted sorting fields will be
    #: retrieved.
    sort_arg = "sort"

    def __init__(self, *field_names, default=None, **kwargs):
        keys = frozenset(kwargs.keys())
        names = frozenset(field_names)
        duplicates = keys.intersection(names)

        if duplicates:
            raise ValueError(
                f"Sort field(s) cannot be passed as both positional and keyword arguments: {duplicates}"
            )

        self._field_names = names.union(keys)
        self._field_sorters = {
            field_name: field_sort for field_name, field_sort in kwargs.items()
        }
        self._default_sort = default

    def get_criterion(self, view, field_ordering):
        field_name, asc = field_ordering

        if field_name not in self._field_sorters:
            return super().get_criterion(view, field_ordering)

        sort = self._field_sorters[field_name]

        expr = sort(view.model, field_name) if callable(sort) else sort

        return expr if asc else sa.desc(expr)

    def get_request_field_orderings(self, view):
        sort = flask.request.args.get(self.sort_arg, self._default_sort)
        if sort is None:
            return ()

        field_orderings = self.get_field_orderings(sort)

        for field_name, _ in field_orderings:
            if field_name not in self._field_names:
                raise ApiError(
                    400,
                    {
                        "code": "invalid_sort",
                        "source": {"parameter": self.sort_arg},
                    },
                )

        return field_orderings
