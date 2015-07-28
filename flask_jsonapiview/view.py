import flask
from flask.views import MethodView, MethodViewType, with_metaclass
from sqlalchemy.orm.exc import NoResultFound

# -----------------------------------------------------------------------------


class JsonApiViewType(MethodViewType):
    def __new__(mcs, name, bases, dct):
        cls = super(JsonApiViewType, mcs).__new__(mcs, name, bases, dct)

        if 'methods' not in dct:
            # Include methods defined by e.g. mixins.
            methods = set(cls.methods or [])
            for base in bases:
                if hasattr(base, 'methods') and base.methods:
                    methods.update(base.methods)
            if methods:
                cls.methods = sorted(methods)

        return cls


class JsonApiView(with_metaclass(JsonApiViewType, MethodView)):
    model = None
    serializer = None
    deserializer = None

    @property
    def session(self):
        return flask.current_app.extensions['sqlalchemy'].db.session

    @property
    def query(self):
        return self.model.query

    def get_item(self, id):
        return self._get_item(id)

    def _get_item(self, id):
        # This base implementation should not be overridden.
        return self.query.filter_by(id=id).one()

    def ensure_item(self, id):
        try:
            item = self._get_item(id)
        except NoResultFound:
            item = self.model(id=id)
            self.session.add(item)

        return item

    def get_item_or_404(self, id):
        # Can't use cls.query.get, because query might be filtered.
        try:
            item = self.get_item(id)
        except NoResultFound:
            flask.abort(404)
        else:
            return item

    def serialize(self, item, **kwargs):
        return self.serializer.dump(item, **kwargs).data

    def make_response_body(self, data, **kwargs):
        return flask.jsonify(
            data=self.serialize(data, **kwargs)
        )

    def deserialize(self, data, **kwargs):
        return self.deserializer.load(data, **kwargs).data

    @property
    def resolvers(self):
        return ()

    def get_request_data(self, expected_id=None, **kwargs):
        try:
            data = flask.request.get_json()['data']
        except KeyError:
            flask.abort(400)
        else:
            # Validate data for endpoint before deserializing - the
            # deserializer most likely will not include the endpoint-level
            # fields that we need to check here.
            self.validate_request_data(data, expected_id)

            data_loaded = self.deserialize(data, **kwargs)
            return self._apply_resolvers(data_loaded)

    def validate_request_data(self, data, expected_id):
        if 'type' not in data:
            flask.abort(400)
        if data['type'] != self.deserializer.opts.type:
            flask.abort(409)

        if expected_id is not None:
            if 'id' not in data:
                flask.abort(400)
            if data['id'] != str(expected_id):
                flask.abort(409)

    def _apply_resolvers(self, data_loaded):
        for field, resolver in self.resolvers:
            if field in data_loaded:
                if self.deserializer.fields[field].many:
                    data_loaded[field] = [
                        resolver(value) for value in data_loaded[field]
                    ]
                else:
                    data_loaded[field] = resolver(data_loaded[field])

        return data_loaded
