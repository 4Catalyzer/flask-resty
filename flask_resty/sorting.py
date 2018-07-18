import flask

from .exceptions import ApiError

# -----------------------------------------------------------------------------


class SortingBase(object):
    def sort_query(self, query, view):
        raise NotImplementedError()


# -----------------------------------------------------------------------------


class FieldSortingBase(SortingBase):
    def sort_query(self, query, view):
        field_orderings = self.get_request_field_orderings(view)
        return self.sort_query_by_fields(query, view, field_orderings)

    def sort_query_by_fields(self, query, view, field_orderings):
        criteria = self.get_criteria(view, field_orderings)
        return query.order_by(*criteria)

    def get_request_field_orderings(self, view):
        raise NotImplementedError()

    def get_field_orderings(self, fields):
        return tuple(
            self.get_field_ordering(field)
            for field in fields.split(',')
        )

    def get_field_ordering(self, field):
        if field and field[0] == '-':
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
    def __init__(self, fields):
        self._field_orderings = self.get_field_orderings(fields)

    def get_request_field_orderings(self, view):
        return self._field_orderings


class Sorting(FieldSortingBase):
    sort_arg = 'sort'

    def __init__(self, *field_names, **kwargs):
        self._field_names = frozenset(field_names)
        self._default_sort = kwargs.get('default')

    def get_request_field_orderings(self, view):
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
