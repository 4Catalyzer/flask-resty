import flask
from flask.views import MethodView
from marshmallow import ValidationError
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm.exc import NoResultFound

from .exceptions import IncorrectTypeError

__all__ = ('ApiView', 'ModelView', 'GenericModelView')

# -----------------------------------------------------------------------------


class ApiView(MethodView):
    schema = None
    serializer = None
    deserializer = None

    allow_client_generated_id = False

    def serialize(self, item, **kwargs):
        serializer = self.serializer or self.schema
        return serializer.dump(item, **kwargs).data

    def make_response(self, data_out, *args):
        body = {'data': data_out}
        meta = self.get_response_meta()
        if meta:
            body['meta'] = meta

        return flask.make_response(flask.jsonify(**body), *args)

    def get_response_meta(self):
        return None

    def make_empty_response(self):
        return flask.make_response('', 204)

    def get_request_data(self, **kwargs):
        try:
            data_raw = flask.request.get_json()['data']
        except KeyError:
            flask.abort(400)
        else:
            return self.deserialize(data_raw, **kwargs)

    def deserialize(self, data_raw, expected_id=None, **kwargs):
        deserializer = self.deserializer or self.schema
        try:
            data = deserializer.load(data_raw, **kwargs).data
        except IncorrectTypeError:
            flask.abort(409)
        except ValidationError:
            flask.abort(422)
        else:
            self.validate_request_id(data, expected_id)
            return data

    def validate_request_id(self, data, expected_id):
        if expected_id is None:
            return

        if expected_id is False:
            if 'id' in data and not self.allow_client_generated_id:
                flask.abort(403)
            return

        try:
            id = data['id']
        except KeyError:
            flask.abort(422)
        else:
            if id != expected_id:
                flask.abort(409)

    def pick(self, data, keys):
        picked = {}
        for key in keys:
            try:
                value = data[key]
            except KeyError:
                flask.abort(422)
            else:
                picked[key] = value

        return picked


class ModelView(ApiView):
    model = None
    url_id_key = 'id'

    @property
    def session(self):
        return flask.current_app.extensions['sqlalchemy'].db.session

    @property
    def query(self):
        return self.model.query

    def get_item_or_404(self, id):
        try:
            item = self.get_item(id)
        except NoResultFound:
            flask.abort(404)
        else:
            return item

    def get_item(self, id):
        try:
            # Can't use self.query.get(), because query might be filtered.
            item = self.query.filter_by(id=id).one()
        except NoResultFound:
            if self.should_create_missing(id):
                item = self.model(id=id)
                self.session.add(item)
            else:
                raise

        return item

    def should_create_missing(self, id):
        return False

    def resolve_nested(self, data, key, api_class, many=False):
        try:
            nested_data = data[key]
        except KeyError:
            # If this field were required, the deserializer already would have
            # raised an exception.
            return

        if many:
            resolved = [
                self.get_related_item(nested_datum, api_class)
                for nested_datum in nested_data
            ]
        else:
            resolved = self.get_related_item(nested_data, api_class)

        data[key] = resolved

    def get_related_item(self, related_data, related_api_class):
        try:
            related_id = related_data['id']
        except KeyError:
            flask.abort(422)
        else:
            related_api = related_api_class()
            try:
                item = related_api.get_item(related_id)
            except NoResultFound:
                flask.abort(422)
            else:
                return item

    def create_item(self, data):
        return self.model(**data)

    def add_item(self, item):
        self.session.add(item)

    def update_item(self, item, data):
        for key, value in data.items():
            setattr(item, key, value)

        return False

    def delete_item(self, item):
        self.session.delete(item)

    def commit(self):
        try:
            self.session.commit()
        except IntegrityError:
            flask.abort(409)
        except DataError:
            flask.abort(422)


class GenericModelView(ModelView):
    def list(self):
        query = self.transform_list_query(self.query)
        collection = query.all()
        data_out = self.serialize(collection, many=True)
        return self.make_response(data_out)

    def transform_list_query(self, query):
        query = self.sort_list_query(query)
        query = self.filter_list_query(query)
        return query

    def sort_list_query(self, query):
        return query.order_by(self.model.id)

    def filter_list_query(self, query):
        return query

    def retrieve(self, id):
        item = self.get_item_or_404(id)
        data_out = self.serialize(item)
        return self.make_response(data_out)

    def create(self):
        data_in = self.get_request_data(expected_id=False)
        item = self.create_item(data_in)

        self.add_item(item)
        self.commit()

        data_out = self.serialize(item)
        location = flask.url_for(
            flask.request.endpoint, **{self.url_id_key: item.id}
        )
        return self.make_response(data_out, 201, {'Location': location})

    def update(self, id):
        item = self.get_item_or_404(id)
        data_in = self.get_request_data(expected_id=id)

        return_content = self.update_item(item, data_in)
        self.commit()

        if return_content:
            data_out = self.serialize(item)
            return self.make_response(data_out)
        else:
            return self.make_empty_response()

    def destroy(self, id):
        item = self.get_item_or_404(id)

        self.delete_item(item)
        self.commit()

        return self.make_empty_response()
