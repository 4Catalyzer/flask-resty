import flask
from flask.views import MethodView
import logging
from marshmallow import ValidationError
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from werkzeug import ImmutableDict

from .authentication import NoOpAuthentication
from .authorization import NoOpAuthorization
from .exceptions import IncorrectTypeError
from . import meta

# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------


class ApiView(MethodView):
    schema = None

    authentication = NoOpAuthentication()
    authorization = NoOpAuthorization()

    def dispatch_request(self, *args, **kwargs):
        self.authentication.authenticate_request()
        self.authorization.authorize_request()

        return super(ApiView, self).dispatch_request(*args, **kwargs)

    def serialize(self, item, **kwargs):
        return self.serializer.dump(item, **kwargs).data

    @property
    def serializer(self):
        return self.schema

    def make_raw_response(self, *args, **kwargs):
        response = flask.make_response(*args)
        for key, value in kwargs.items():
            setattr(response, key, value)
        return response

    def make_response(self, data_out, *args, **kwargs):
        body = {'data': data_out}

        response_meta = meta.get_response_meta()
        if response_meta is not None:
            body['meta'] = response_meta

        return self.make_raw_response(flask.jsonify(**body), *args, **kwargs)

    def make_empty_response(self, **kwargs):
        return self.make_raw_response('', 204, **kwargs)

    def get_request_data(self, **kwargs):
        try:
            data_raw = flask.request.get_json()['data']
        except TypeError:
            logger.warning("payload is not a JSON object")
            flask.abort(400)
        except KeyError:
            logging.warning("no data member in request")
            flask.abort(400)
        else:
            return self.deserialize(data_raw, **kwargs)

    def deserialize(self, data_raw, expected_id=None, **kwargs):
        try:
            data = self.deserializer.load(data_raw, **kwargs).data
        except IncorrectTypeError:
            logger.warning("incorrect type in request data", exc_info=True)
            flask.abort(409)
        except ValidationError:
            logger.warning("invalid request data", exc_info=True)
            flask.abort(422)
        else:
            self.validate_request_id(data, expected_id)
            return data

    @property
    def deserializer(self):
        return self.schema

    def validate_request_id(self, data, expected_id):
        if expected_id is None:
            return

        if expected_id is False:
            if 'id' in data:
                logger.warning("client generated id not allowed")
                flask.abort(403)
            return

        try:
            id = data['id']
        except KeyError:
            logger.warning("no id in request data")
            flask.abort(422)
        else:
            if id != expected_id:
                logger.warning(
                    "incorrect id in request data, got {} but expected {}"
                    .format(id, expected_id)
                )
                flask.abort(409)


class ModelView(ApiView):
    model = None
    url_id_key = 'id'

    nested = ImmutableDict()

    sorting = None
    filtering = None
    pagination = None

    @property
    def session(self):
        return flask.current_app.extensions['sqlalchemy'].db.session

    @property
    def query(self):
        query = self.model.query
        query = self.authorization.filter_query(query, self)

        return query

    def get_list(self):
        list_query = self.query

        list_query = self.sort_list_query(list_query)
        list_query = self.filter_list_query(list_query)

        # Pagination is special because it has to own executing the query.
        return self.paginate_list_query(list_query)

    def sort_list_query(self, query):
        if not self.sorting:
            return query

        return self.sorting(query, self)

    def filter_list_query(self, query):
        if not self.filtering:
            return query

        return self.filtering(query, self)

    def paginate_list_query(self, query):
        if not self.pagination:
            return query.all()

        return self.pagination(query, self)

    def get_item_or_404(self, id, **kwargs):
        try:
            item = self.get_item(id, **kwargs)
        except NoResultFound:
            logger.warning("no item with id {}".format(id))
            flask.abort(404)
        else:
            return item

    def get_item(self, id, create_missing=False):
        try:
            # Can't use self.query.get(), because query might be filtered.
            item = self.query.filter_by(id=id).one()
        except NoResultFound:
            if create_missing:
                item = self.create_missing_item(id)
                self.session.add(item)
                return item
            else:
                raise
        except DataError:
            logger.warning(
                "failed to get item with id {}".format(id), exc_info=True
            )
            flask.abort(400)
        else:
            return item

    def deserialize(self, data_raw, **kwargs):
        data = super(ModelView, self).deserialize(data_raw, **kwargs)

        for key, view_class in self.nested.items():
            many = self.deserializer.fields[key].many
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
        try:
            related_id = related_data['id']
        except KeyError:
            logger.warning("no id specified for related item")
            flask.abort(422)
        else:
            try:
                item = related_view.get_item(related_id)
            except NoResultFound:
                logger.warning("no related item with id {}".format(id))
                flask.abort(422)
            else:
                return item

    def create_missing_item(self, id):
        return self.create_item({'id': id})

    def create_item(self, data):
        return self.model(**data)

    def add_item(self, item):
        self.session.add(item)

        self.authorization.authorize_save_item(item)

    def update_item(self, item, data):
        self.authorization.authorize_update_item(item, data)

        for key, value in data.items():
            setattr(item, key, value)

        self.authorization.authorize_save_item(item)

    def delete_item(self, item):
        self.authorization.authorize_delete_item(item)

        self.session.delete(item)

    def commit(self):
        try:
            self.session.commit()
        except IntegrityError:
            logger.warning("failed to commit change", exc_info=True)
            flask.abort(409)
        except DataError:
            logger.warning("failed to commit change", exc_info=True)
            flask.abort(422)

    def make_item_response(self, item, *args):
        data_out = self.serialize(item)
        return self.make_response(data_out, *args, item=item)

    def make_created_response(self, item):
        location = flask.url_for(
            flask.request.endpoint, **{self.url_id_key: item.id}
        )
        return self.make_item_response(item, 201, {'Location': location})


class GenericModelView(ModelView):
    def list(self):
        items = self.get_list()
        data_out = self.serialize(items, many=True)
        return self.make_response(data_out, items=items)

    def retrieve(self, id, create_missing=False):
        item = self.get_item_or_404(id, create_missing=create_missing)
        return self.make_item_response(item)

    def create(self, allow_client_id=False):
        expected_id = None if allow_client_id else False
        data_in = self.get_request_data(expected_id=expected_id)
        item = self.create_item(data_in)

        self.add_item(item)
        self.commit()

        return self.make_created_response(item)

    def update(self, id, create_missing=False, return_content=False):
        item = self.get_item_or_404(id, create_missing=create_missing)
        data_in = self.get_request_data(expected_id=id)

        self.update_item(item, data_in)
        self.commit()

        if return_content:
            return self.make_item_response(item)
        else:
            return self.make_empty_response(item=item)

    def destroy(self, id):
        item = self.get_item_or_404(id)

        self.delete_item(item)
        self.commit()

        return self.make_empty_response()
