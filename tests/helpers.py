import json

# -----------------------------------------------------------------------------


def request(client, method, path, data, **kwargs):
    return client.open(
        path,
        method=method,
        content_type='application/json',
        data=json.dumps({'data': data}),
        **kwargs
    )


# -----------------------------------------------------------------------------


def get_body(response):
    assert response.mimetype == 'application/json'
    return json.loads(response.data)


def get_data(response):
    return get_body(response)['data']


def get_meta(response):
    return get_body(response)['meta']


def get_errors(response):
    return get_body(response)['errors']
