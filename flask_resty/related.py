import flask
import logging
from sqlalchemy.orm.exc import NoResultFound

# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------


class RelatedBase(object):
    def __init__(self, **kwargs):
        self._view_classes = kwargs

    def __call__(self, data, view):
        for key, view_class in self._view_classes.items():
            many = view.deserializer.fields[key].many
            self.resolve_nested(data, key, view_class, many=many)

        return data

    def resolve_nested(self, data, key, view_class, many=False):
        try:
            nested_data = data[key]
        except KeyError:
            # If this field were required, the deserializer already would have
            # raised an exception.
            return

        if many:
            if not nested_data:
                resolved = []
            else:
                view = view_class()
                resolved = [
                    self.get_related_item(nested_datum, view)
                    for nested_datum in nested_data
                ]
        else:
            resolved = self.get_related_item(nested_data, view_class())

        data[key] = resolved

    def get_related_item(self, related_data, related_view):
        related_id = self.get_related_id(related_data, related_view)

        try:
            related_item = related_view.get_item(related_id)
        except NoResultFound:
            logger.warning("no related item with id {}".format(id))
            flask.abort(422)
        else:
            return related_item

    def get_related_id(self, related_data, related_view):
        raise NotImplementedError()


class NestedRelated(RelatedBase):
    def get_related_id(self, related_data, related_view):
        try:
            related_id = related_data['id']
        except KeyError:
            logger.warning("no id specified for related item")
            flask.abort(422)
        else:
            return related_id
