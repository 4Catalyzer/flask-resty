import flask

# -----------------------------------------------------------------------------


def register_api(app, endpoint,
                 collection_rule, collection_view,
                 item_rule, item_view):
    """Helper function for registering APIs

    This will set up a single view function that lets us register both the
    collection and item APIs at the same endpoint, to allow returning the
    location for a new object after creation.
    """
    collection_view_func = collection_view.as_view(endpoint)
    item_view_func = item_view.as_view(endpoint)

    def view_func(*args, **kwargs):
        if flask.request.url_rule.rule == collection_rule:
            return collection_view_func(*args, **kwargs)
        else:
            return item_view_func(*args, **kwargs)

    app.add_url_rule(collection_rule, view_func=view_func, endpoint=endpoint,
                     methods=collection_view.methods)
    app.add_url_rule(item_rule, view_func=view_func, endpoint=endpoint,
                     methods=item_view.methods)
