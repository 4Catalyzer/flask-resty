import flask

from .exceptions import ApiError

# -----------------------------------------------------------------------------


class SortingBase(object):
    def __call__(self, query, view):
        raise NotImplementedError()

    def get_field_specs(self, fields):
        return tuple(
            self.get_field_spec(field) for field in fields.split(',')
        )

    def get_field_spec(self, field):
        if field and field[0] == '-':
            return field[1:], False

        return field, True

    def sort_query(self, query, view, field_specs):
        criteria = self.get_criteria(view, field_specs)
        return query.order_by(*criteria)

    def get_criteria(self, view, field_specs):
        return tuple(
            self.get_criterion(view, field_spec) for field_spec in field_specs
        )

    def get_criterion(self, view, field_spec):
        field_name, asc = field_spec
        column = self.get_column(view, field_name)
        return column if asc else column.desc()

    def get_column(self, view, field_name):
        return getattr(view.model, field_name)


# -----------------------------------------------------------------------------


class FixedSorting(SortingBase):
    def __init__(self, fields):
        self._field_specs = self.get_field_specs(fields)

    def __call__(self, query, view):
        return self.sort_query(query, view, self._field_specs)


class Sorting(SortingBase):
    sort_arg = 'sort'

    def __init__(self, *field_names, **kwargs):
        self._field_names = frozenset(field_names)
        self._default_sort = kwargs.get('default')

    def __call__(self, query, view):
        sort = flask.request.args.get(self.sort_arg, self._default_sort)
        if sort is None:
            return query

        return self.sort_query(query, view, self.get_field_specs(sort))

    def get_column(self, view, field_name):
        if field_name not in self._field_names:
            raise ApiError(400, {
                'code': 'invalid_sort',
                'source': {'parameter': self.sort_arg},
            })

        return super(Sorting, self).get_column(view, field_name)

    def spec_declaration(self, path, spec, **kwargs):
        path['get'].add_parameter(
            name='sort',
            type='string',
            description='field to sort by')
