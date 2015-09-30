from . import utils

# -----------------------------------------------------------------------------


class SortingBase(object):
    def __call__(self, query, view):
        raise NotImplementedError()

    def get_field_specs(self, fields):
        if not fields:
            raise ValueError("fields must not be empty")

        return tuple(
            self.get_field_spec(field) for field in fields.split(',')
        )

    def get_field_spec(self, field):
        if not field:
            raise ValueError("field must not be empty")

        if field[0] == '-':
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
        self.validate_field_name(view, field_name)
        column_name = utils.current_api.parse_key(field_name)
        return getattr(view.model, column_name)

    def validate_field_name(self, view, field_name):
        raise NotImplementedError()


# -----------------------------------------------------------------------------


class FixedSorting(SortingBase):
    def __init__(self, fields):
        self._field_specs = self.get_field_specs(fields)

    def __call__(self, query, view):
        return self.sort_query(query, view, self._field_specs)

    def validate_field_name(self, field_name, view):
        return True
