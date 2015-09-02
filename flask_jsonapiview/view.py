import flask
from flask.views import MethodView
from sqlalchemy.orm.exc import NoResultFound

__all__ = ('ApiView', 'ModelView', 'GenericModelView')

# -----------------------------------------------------------------------------


class ApiView(MethodView):
    serializer = None
    deserializer = None

    def serialize(self, item, **kwargs):
        return self.serializer.dump(item, **kwargs).data

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

    def get_request_data(self, expected_id=None, **kwargs):
        try:
            data_in_raw = flask.request.get_json()['data']
        except KeyError:
            flask.abort(400)
        else:
            # Validate data for endpoint before deserializing - the
            # deserializer most likely will not include the endpoint-level
            # fields that we need to check here.
            self.validate_request_data(data_in_raw, expected_id)

            return self.deserialize(data_in_raw, **kwargs)

    def validate_request_data(self, data_in_raw, expected_id):
        if 'type' not in data_in_raw:
            flask.abort(400)
        if data_in_raw['type'] != self.deserializer.opts.type:
            flask.abort(409)

        if expected_id is not None:
            if 'id' not in data_in_raw:
                flask.abort(400)
            if data_in_raw['id'] != str(expected_id):
                flask.abort(409)

    def deserialize(self, data_in_raw, **kwargs):
        return self.deserializer.load(data_in_raw, **kwargs).data


class ModelView(ApiView):
    model = None

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


class GenericModelView(ModelView):
    url_id_key = 'id'

    def list(self):
        query = self.transform_list_query(self.query)
        collection = query.all()
        data_out = self.serialize(collection, many=True)
        return self.make_response(data_out)

    def transform_list_query(self, query):
        query = self.apply_sort(query)
        query = self.apply_filters(query)
        return query

    def apply_filters(self, query):
        return query

    def apply_sort(self, query):
        return query.order_by(self.model.id)

    def retrieve(self, id):
        item = self.get_item_or_404(id)
        data_out = self.serialize(item)
        return self.make_response(data_out)

    def create(self):
        data_in = self.get_request_data()
        item = self.create_item(data_in)

        self.session.add(item)
        self.session.commit()

        data_out = self.serialize(item)
        location = flask.url_for(
            flask.request.endpoint, **{self.url_id_key: item.id}
        )
        return self.make_response(data_out, 201, {'Location': location})

    def create_item(self, data_in):
        return self.model(**data_in)

    def update(self, id):
        item = self.get_item_or_404(id)
        data_in = self.get_request_data(expected_id=id)

        return_content = self.update_item(item, data_in)
        self.session.commit()

        if return_content:
            data_out = self.serialize(item)
            return self.make_response(data_out)
        else:
            return self.make_empty_response()

    def update_item(self, item, data_in):
        for key, value in data_in.items():
            setattr(item, key, value)

        return False

    def destroy(self, id):
        item = self.get_item_or_404(id)

        self.session.delete(item)
        self.session.commit()

        return self.make_empty_response()
