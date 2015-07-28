import flask
from sqlalchemy.orm.exc import NoResultFound

from .view import JsonApiView

# -----------------------------------------------------------------------------


class GetManyMixin(JsonApiView):
    def get(self):
        query = self.query

        query = self.apply_request_filters(query)
        query = self.apply_sort(query)

        collection = query.all()
        return flask.make_response(
            self.make_response_body(collection, many=True)
        )

    def apply_request_filters(self, query):
        return query

    def apply_sort(self, query):
        return query.order_by(self.model.id)


class GetSingleMixin(JsonApiView):
    def get(self, id):
        item = self.get_item_or_404(id)
        return flask.make_response(
            self.make_response_body(item)
        )


class PostMixin(JsonApiView):
    def post(self):
        data = self.get_request_data()
        item = self.create_item(data)

        self.session.add(item)
        self.session.commit()

        location = flask.url_for(flask.request.endpoint, id=item.id)
        return flask.make_response(
            self.make_response_body(item),
            201,
            {'Location': location}
        )

    def create_item(self, data_loaded):
        return self.model(**data_loaded)


class PatchMixin(JsonApiView):
    def patch(self, id):
        item = self.get_item_or_404(id)
        data = self.get_request_data(expected_id=id)

        return_content = self.update_item(item, data)
        self.session.commit()

        if return_content:
            return flask.make_response(
                self.make_response_body(item)
            )
        else:
            return flask.make_response('', 204)

    def update_item(self, item, data):
        for key, value in data.items():
            setattr(item, key, value)

        return False


class PutAsPatchMixin(PatchMixin):
    methods = ('PUT',)
    create_on_put = False

    def put(self, id):
        return self.patch(id)

    def get_item(self, id):
        if flask.request.method == 'PUT' and self.create_on_put:
            return self.ensure_item(id)

        return super(PutAsPatchMixin, self).get_item(id)


class DeleteMixin(JsonApiView):
    def delete(self, id):
        item = self.get_item_or_404(id)

        self.session.delete(item)
        self.session.commit()

        return flask.make_response('', 204)
