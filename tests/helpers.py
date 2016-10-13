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
