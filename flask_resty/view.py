import flask
from flask.views import MethodView
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.exceptions import NotFound

from .authentication import NoOpAuthentication
from .authorization import NoOpAuthorization
from .exceptions import ApiError
from . import meta
from . import utils

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

    def make_response(self, data, *args, **kwargs):
        body = self.make_response_body(data, meta.get_response_meta())
        return self.make_raw_response(flask.jsonify(**body), *args, **kwargs)

    def make_response_body(self, data, response_meta):
        body = {'data': data}
        if response_meta is not None:
            body['meta'] = response_meta

        return body

    def make_raw_response(self, *args, **kwargs):
        response = flask.make_response(*args)
        for key, value in kwargs.items():
            setattr(response, key, value)
        return response

    def make_empty_response(self, **kwargs):
        return self.make_raw_response('', 204, **kwargs)

    def get_request_data(self, **kwargs):
        try:
            data_raw = flask.request.get_json()['data']
        except TypeError:
            raise ApiError(400, {'code': 'invalid_body'})
        except KeyError:
            raise ApiError(400, {'code': 'invalid_data.missing'})

        return self.deserialize(data_raw, **kwargs)

    def deserialize(self, data_raw, expected_id=None, **kwargs):
        data, errors = self.deserializer.load(data_raw, **kwargs)
        if errors:
            formatted_errors = (
                self.format_validation_error(error)
                for error in utils.iter_validation_errors(errors)
            )
            raise ApiError(422, *formatted_errors)

        self.validate_request_id(data, expected_id)
        return data

    @property
    def deserializer(self):
        return self.schema

    def format_validation_error(self, error):
        message, path = error
        pointer = '/data/{}'.format(
            '/'.join(str(field_key) for field_key in path),
        )

        return {
            'code': 'invalid_data',
            'detail': message,
            'source': {'pointer': pointer},
        }

    def validate_request_id(self, data, expected_id):
        if expected_id is None:
            return

        if expected_id is False:
            if 'id' in data:
                raise ApiError(403, {'code': 'invalid_id.forbidden'})
            return

        try:
            id = data['id']
        except KeyError:
            raise ApiError(422, {'code': 'invalid_id.missing'})

        if id != expected_id:
            raise ApiError(409, {'code': 'invalid_id.mismatch'})


class ModelView(ApiView):
    model = None
    id_view_arg = 'id'

    sorting = None
    filtering = None
    pagination = None

    related = None

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
            raise NotFound()

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

            raise
        except DataError:
            raise ApiError(400, {'code': 'invalid_id'})

        return item

    def deserialize(self, data_raw, **kwargs):
        data = super(ModelView, self).deserialize(data_raw, **kwargs)
        if not self.related:
            return data

        return self.related(data, self)

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
            raise ApiError(409, {'code': 'invalid_data.conflict'})
        except DataError:
            raise ApiError(422, {'code': 'invalid_data'})

    def make_item_response(self, item, *args):
        data_out = self.serialize(item)
        return self.make_response(data_out, *args, item=item)

    def make_created_response(self, item):
        location = flask.url_for(
            flask.request.endpoint, _method='GET',
            **{self.id_view_arg: item.id}
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

    def update(
            self, id, create_missing=False, partial=False,
            return_content=False):
        item = self.get_item_or_404(id, create_missing=create_missing)
        data_in = self.get_request_data(expected_id=id, partial=partial)

        self.update_item(item, data_in)
        self.commit()

        if return_content:
            return self.make_item_response(item)

        return self.make_empty_response(item=item)

    def destroy(self, id):
        item = self.get_item_or_404(id)

        self.delete_item(item)
        self.commit()

        return self.make_empty_response()
