from __future__ import absolute_import

import flask
import jwt
from jwt import InvalidTokenError

from .authentication import AuthenticationBase
from .exceptions import ApiError

# -----------------------------------------------------------------------------

JWT_DECODE_ARG_KEYS = (
    'key',
    'verify',
    'algorithms',
    'options',
    'audience',
    'issuer',
    'leeway',
)

# -----------------------------------------------------------------------------


class JwtAuthentication(AuthenticationBase):
    CONFIG_KEY_TEMPLATE = 'RESTY_JWT_DECODE_{}'

    header_scheme = 'Bearer'
    id_token_arg = 'id_token'

    def __init__(self, **kwargs):
        super(JwtAuthentication, self).__init__()

        self._decode_args = {
            key: kwargs[key] for key in JWT_DECODE_ARG_KEYS if key in kwargs
        }

    def get_request_credentials(self):
        token = self.get_token()
        if not token:
            return None

        try:
            payload = self.decode_token(token)
        except InvalidTokenError:
            raise ApiError(401, {'code': 'invalid_token'})

        return self.get_credentials(payload)

    def get_token(self):
        authorization = flask.request.headers.get('Authorization')
        if authorization:
            token = self.get_token_from_authorization(authorization)
        else:
            token = self.get_token_from_request()

        return token

    def get_token_from_authorization(self, authorization):
        try:
            scheme, token = authorization.split()
        except ValueError:
            raise ApiError(401, {'code': 'invalid_authorization'})

        if scheme != self.header_scheme:
            raise ApiError(401, {'code': 'invalid_authorization.scheme'})

        return token

    def get_token_from_request(self):
        return flask.request.args.get(self.id_token_arg)

    def decode_token(self, token):
        return jwt.decode(token, **self.get_jwt_decode_args())

    def get_jwt_decode_args(self):
        config = flask.current_app.config
        args = {
            key: config[self.get_config_key(key)]
            for key in JWT_DECODE_ARG_KEYS
            if self.get_config_key(key) in config
        }

        args.update(self._decode_args)
        return args

    def get_config_key(self, key):
        return self.CONFIG_KEY_TEMPLATE.format(key.upper())

    def get_credentials(self, payload):
        return payload
