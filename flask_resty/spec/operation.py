class Operation(dict):
    """Exposes some utility methods to compose a swagger operation
    https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#operation-object
    """

    def __init__(self):
        super(Operation, self).__init__({
            'responses': {},
            'parameters': []
        })

    def add_parameter(self, location='query', **kwargs):
        """Adds a new parameter to the request
        :param location: the 'in' field of the parameter (e.g: 'query',
            'body', 'path')
        """
        kwargs.setdefault('in', location)
        if kwargs['in'] != 'body':
            kwargs.setdefault('type', 'string')
        self['parameters'].append(kwargs)
        pass

    def add_property_to_response(self, code='200', prop_name='data', **kwargs):
        """Add a property (http://json-schema.org/latest/json-schema-validation.html#anchor64) # noqa
        to the schema of the response identified by the code"""
        self['responses']\
            .setdefault(str(code), self._new_operation())\
            .setdefault('schema', {'type': 'object'})\
            .setdefault('properties', {})\
            .setdefault(prop_name, {})\
            .update(**kwargs)

    def declare_response(self, code='200', **kwargs):
        """Declare a response for the specified code
        https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#responseObject # noqa"""
        self['responses'][str(code)] = self._new_operation(**kwargs)

    def add_tag(self, tag):
        """Add a tag to the operation"""
        self.setdefault('tags', []).append(tag)

    def _new_operation(self, **kwargs):
        kwargs.setdefault('description', '')
        return dict(kwargs)
