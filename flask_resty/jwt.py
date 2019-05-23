import base64
import json

from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_der_x509_certificate
import flask
import jwt
from jwt import InvalidAlgorithmError, InvalidTokenError, PyJWT

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
        super().__init__()

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

        if scheme.lower() != self.header_scheme.lower():
            raise ApiError(401, {'code': 'invalid_authorization.scheme'})

        return token

    def get_token_from_request(self):
        return flask.request.args.get(self.id_token_arg)

    def decode_token(self, token):
        return self.pyjwt.decode(token, **self.get_jwt_decode_args())

    @property
    def pyjwt(self):
        return jwt

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


class JwkSetPyJwt(PyJWT):
    def __init__(self, jwk_set, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.jwk_set = jwk_set

    def decode(self, jwt, **kwargs):
        unverified_header = self.get_unverified_header(jwt)

        jwk = self.get_jwk_from_jwt(unverified_header)

        # It's safe to use alg from the header here, as we verify that against
        # the algorithm whitelist.
        alg = jwk['alg'] if 'alg' in jwk else unverified_header['alg']

        # jwt.decode will also check this, but this is more defensive.
        if alg not in kwargs['algorithms']:
            raise InvalidAlgorithmError(
                "The specified alg value is not allowed",
            )

        return super().decode(
            jwt,
            key=self.get_key_from_jwk(jwk, alg),
            **kwargs,
        )

    def get_jwk_from_jwt(self, unverified_header):
        try:
            token_kid = unverified_header['kid']
        except KeyError:
            raise InvalidTokenError("Key ID header parameter is missing")

        for jwk in self.jwk_set['keys']:
            if jwk['kid'] == token_kid:
                return jwk

        raise InvalidTokenError("no key found")

    def get_key_from_jwk(self, jwk, alg):
        if 'x5c' in jwk:
            return load_der_x509_certificate(
                base64.b64decode(jwk['x5c'][0]),
                default_backend(),
            ).public_key()

        algorithm = self._algorithms[alg]

        # Awkward:
        return algorithm.from_jwk(json.dumps(jwk))


class JwkSetAuthentication(JwtAuthentication):
    def __init__(self, jwk_set=None, **kwargs):
        super().__init__(**kwargs)

        self._jwk_set = jwk_set

    @property
    def pyjwt(self):
        return JwkSetPyJwt(self.jwk_set)

    @property
    def jwk_set(self):
        return (
            self._jwk_set or
            flask.current_app.config[self.get_config_key('jwk_set')]
        )
