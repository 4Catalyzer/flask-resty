from flask.views import http_method_funcs

from .utils import get_marshmallow_schema_name, ref


class ApiViewDeclaration(object):
    """Simple Declaration for ApiView Classes
    :param many: whether or not this view describes a list or a single instance
    :param tag: whether or not the schema name should be added as a tag"""

    def __init__(self, many=False, tag=True, **kwargs):
        self.many = many
        self.tag = tag

        invalid_kwargs = list(set(kwargs.keys()) - http_method_funcs)
        if invalid_kwargs:
            raise TypeError(
                'invalid keyword argument "{}"'.format(invalid_kwargs[0]))

        self.overrides = kwargs

    def __call__(self, view, path, spec):
        view_methods = set(view.__dict__.keys()) \
            .intersection(http_method_funcs)

        for method in view_methods:
            operation = path[method]  # triggers the operation generation
            if getattr(view, method).__doc__:
                # add docstring as description
                operation['description'] = getattr(view, method).__doc__

        if view.schema:
            self.declare_schema(view, view_methods, path, spec)

        for method in view_methods.intersection(self.overrides.keys()):
            for code, response in self.overrides[method].items():
                path[method].declare_response(code, **response)

    def declare_schema(self, view, view_methods, path, spec):
        schema = get_marshmallow_schema_name(spec, type(view.schema))
        schema_ref = ref(schema)

        if 'get' in view_methods:
            if not self.many:
                data = schema_ref
            else:
                data = {
                    'type': 'array',
                    'items': schema_ref
                }
            path['get'].add_property_to_response(prop_name='data', **data)

        body_params = {
            'name': '{}Payload'.format(schema),
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['data'],
                'properties': {'data': schema_ref}
            }
        }

        if 'post' in view_methods:
            path['post'].add_parameter('body', **body_params)
            path['post'].declare_response(201)

        if 'put' in view_methods:
            path['put'].add_parameter('body', **body_params)
            path['put'].declare_response(204)

        if 'patch' in view_methods:
            path['patch'].add_parameter('body', **body_params)
            path['patch'].add_property_to_response(prop_name='data',
                                                   **schema_ref)

        if 'delete' in view_methods:
            path['delete'].declare_response(204)

        if self.tag:
            for method in view_methods:
                path[method].add_tag(schema)


class ModelViewDeclaration(ApiViewDeclaration):
    """Declaration for Views that specify a model"""

    def __call__(self, view, path, spec):
        super(ModelViewDeclaration, self)\
            .__call__(view, path, spec)

        for item in (view.pagination, view.filtering, view.sorting):
            try:
                item.spec_declaration(path, spec)
            except AttributeError:
                pass
