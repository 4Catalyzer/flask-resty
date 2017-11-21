from __future__ import absolute_import

import base64
import json

from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_der_x509_certificate
import flask
import jwt
from jwt import InvalidTokenError
from jwt.algorithms import get_default_algorithms

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


class JwkSetAuthentication(JwtAuthentication):
    def __init__(self, key_set=None, **kwargs):
        super(JwkSetAuthentication, self).__init__(**kwargs)

        self.jwks = key_set
        self.algorithms = get_default_algorithms()

    def get_jwks(self):
        config = flask.current_app.config
        return self.jwks \
            if self.jwks else config[self.get_config_key('key_set')]

    def from_jwk(self, jwk, algorithm):
        if 'x5c' in jwk:
            return load_der_x509_certificate(
                base64.b64decode(jwk['x5c'][0]),
                default_backend(),
            ).public_key()

        # awkward
        return algorithm.from_jwk(json.dumps(jwk))

    def get_key_for_token(self, token):
        unverified_header = jwt.get_unverified_header(token)

        try:
            algorithm = self.algorithms[unverified_header['alg']]
        except KeyError:
            raise InvalidTokenError('Algorithm header parameter is missing')

        try:
            token_kid = unverified_header['kid']
        except KeyError:
            raise InvalidTokenError('Key ID header parameter is missing')

        for jwk in self.get_jwks()['keys']:
            if jwk['kid'] == token_kid:
                return self.from_jwk(jwk, algorithm)

        raise InvalidTokenError("no key found")

    def decode_token(self, token):
        args = self.get_jwt_decode_args()

        args['key'] = self.get_key_for_token(token)
        print(jwt.decode(token, **args))

        return jwt.decode(token, **args)
