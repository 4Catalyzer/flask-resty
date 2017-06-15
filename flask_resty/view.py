import flask
from flask.views import MethodView
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.exceptions import NotFound

from .authentication import NoOpAuthentication
from .authorization import NoOpAuthorization
from .exceptions import ApiError
from . import meta
from .spec import ApiViewDeclaration, ModelViewDeclaration
from .utils import iter_validation_errors, settable_property

# -----------------------------------------------------------------------------


class ApiView(MethodView):
    schema = None
    id_fields = ('id',)

    authentication = NoOpAuthentication()
    authorization = NoOpAuthorization()

    spec_declaration = ApiViewDeclaration()

    def dispatch_request(self, *args, **kwargs):
        self.authentication.authenticate_request()
        self.authorization.authorize_request()

        return super(ApiView, self).dispatch_request(*args, **kwargs)

    def serialize(self, item, **kwargs):
        return self.serializer.dump(item, **kwargs).data

    @settable_property
    def serializer(self):
        return self.schema

    def make_items_response(self, items, *args):
        data_out = self.serialize(items, many=True)
        return self.make_response(data_out, *args, items=items)

    def make_item_response(self, item, *args):
        data_out = self.serialize(item)
        self.set_item_meta(item)
        return self.make_response(data_out, *args, item=item)

    def set_item_meta(self, item):
        pass

    def make_response(self, data, *args, **kwargs):
        body = self.make_response_body(data, meta.get_response_meta())
        return self.make_raw_response(flask.jsonify(body), *args, **kwargs)

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

    def make_created_response(self, item):
        response = self.make_item_response(item, 201)
        location = self.get_location(item)
        if location is not None:
            response.headers['Location'] = location
        return response

    def get_location(self, item):
        id_dict = {
            id_field: getattr(item, id_field) for id_field in self.id_fields
        }
        return flask.url_for(flask.request.endpoint, _method='GET', **id_dict)

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
                for error in iter_validation_errors(errors)
            )
            raise ApiError(422, *formatted_errors)

        self.validate_request_id(data, expected_id)
        return data

    @settable_property
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
            for id_field in self.id_fields:
                if id_field in data:
                    raise ApiError(403, {'code': 'invalid_id.forbidden'})
            return

        try:
            id = self.get_data_id(data)
        except KeyError:
            raise ApiError(422, {'code': 'invalid_id.missing'})

        if id != expected_id:
            raise ApiError(409, {'code': 'invalid_id.mismatch'})

    def get_data_id(self, data):
        if len(self.id_fields) == 1:
            return data[self.id_fields[0]]

        return tuple(data[id_field] for id_field in self.id_fields)

    def get_id_dict(self, id):
        if len(self.id_fields) == 1:
            id = (id,)

        return dict(zip(self.id_fields, id))


class ModelView(ApiView):
    model = None

    sorting = None
    filtering = None
    pagination = None

    related = None

    spec_declaration = ModelViewDeclaration()

    @settable_property
    def session(self):
        return flask.current_app.extensions['sqlalchemy'].db.session

    @settable_property
    def query(self):
        query = self.model.query
        query = self.authorization.filter_query(query, self)

        return query

    def get_list(self):
        return self.paginate_list_query(self.get_list_query())

    def get_list_query(self):
        query = self.query
        query = self.sort_list_query(query)
        query = self.filter_list_query(query)
        return query

    def sort_list_query(self, query):
        if not self.sorting:
            return query

        return self.sorting.sort_query(query, self)

    def filter_list_query(self, query):
        if not self.filtering:
            return query

        return self.filtering.filter_query(query, self)

    def paginate_list_query(self, query):
        if not self.pagination:
            return query.all()

        return self.pagination.get_page(query, self)

    def get_item_or_404(self, id, **kwargs):
        try:
            item = self.get_item(id, **kwargs)
        except NoResultFound:
            raise NotFound()

        return item

    def get_item(self, id, create_missing=False, for_update=False):
        try:
            # Can't use self.query.get(), because query might be filtered.
            item = self.query.filter(and_(
                getattr(self.model, field) == value
                for field, value in self.get_id_dict(id).items()
            )).one()
        except NoResultFound as e:
            if create_missing:
                item = self.create_missing_item(id)
                if for_update:
                    # Bypass authorizating the save if we are getting the item
                    # for update, as update_item will make that check.
                    self.session.add(item)
                else:
                    try:
                        self.add_item(item)
                    except ApiError:
                        # Raise the original not found error instead of the
                        # authorization error.
                        raise e

                return item

            raise

        return item

    def deserialize(self, data_raw, **kwargs):
        data = super(ModelView, self).deserialize(data_raw, **kwargs)
        return self.resolve_related(data)

    def resolve_related(self, data):
        if not self.related:
            return data

        return self.related.resolve_related(data)

    def resolve_related_item(self, data):
        try:
            id = self.get_data_id(data)
        except KeyError:
            raise ApiError(422, {'code': 'invalid_related.missing_id'})

        try:
            item = self.get_item(id)
        except NoResultFound:
            raise ApiError(422, {'code': 'invalid_related.not_found'})

        return item

    def create_missing_item(self, id):
        return self.create_item(self.get_id_dict(id))

    def create_item(self, data):
        return self.model(**data)

    def add_item(self, item):
        self.session.add(item)

        self.authorization.authorize_save_item(item)

    def create_and_add_item(self, data):
        item = self.create_item(data)
        self.add_item(item)
        return item

    def update_item(self, item, data):
        self.authorization.authorize_update_item(item, data)

        for key, value in data.items():
            setattr(item, key, value)

        self.authorization.authorize_save_item(item)

    def delete_item(self, item):
        self.authorization.authorize_delete_item(item)

        self.session.delete(item)

    def flush(self):
        try:
            # Flushing allows checking invariants without committing.
            self.session.flush()
        except IntegrityError:
            raise ApiError(409, {'code': 'invalid_data.conflict'})

    def commit(self):
        try:
            self.session.commit()
        except IntegrityError:
            raise ApiError(409, {'code': 'invalid_data.conflict'})

    def set_item_meta(self, item):
        super(ModelView, self).set_item_meta(item)
        self.set_item_pagination_meta(item)

    def set_item_pagination_meta(self, item):
        if not self.pagination:
            return

        pagination_meta = self.pagination.get_item_meta(item, self)
        if pagination_meta is not None:
            meta.set_response_meta(**pagination_meta)


class GenericModelView(ModelView):
    def list(self):
        items = self.get_list()
        return self.make_items_response(items)

    def retrieve(self, id, create_missing=False):
        item = self.get_item_or_404(id, create_missing=create_missing)
        return self.make_item_response(item)

    def create(self, allow_client_id=False):
        expected_id = None if allow_client_id else False
        data_in = self.get_request_data(expected_id=expected_id)

        item = self.create_and_add_item(data_in)
        self.commit()

        return self.make_created_response(item)

    def update(
        self, id, create_missing=False, partial=False, return_content=False,
    ):
        # No need to authorize creating the missing item, as we will authorize
        # before saving to database below.
        item = self.get_item_or_404(
            id, create_missing=create_missing, for_update=True,
        )
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
