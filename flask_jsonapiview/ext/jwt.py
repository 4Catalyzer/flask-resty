from __future__ import absolute_import

import flask
import jwt
from jwt import InvalidTokenError
import logging

from ..authentication import AuthenticationBase

# -----------------------------------------------------------------------------

JWT_DECODE_ARG_KEYS = (
    'key',
    'verify',
    'algorithms',
    'options',
    'audience',
    'issuer',
    'leeway'
)

# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------


class JwtAuthentication(AuthenticationBase):
    CONFIG_KEY_TEMPLATE = 'JSONAPIVIEW_JWT_DECODE_{}'

    def __init__(self, **kwargs):
        super(JwtAuthentication, self).__init__()

        self._decode_args = {
            key: kwargs[key] for key in JWT_DECODE_ARG_KEYS if key in kwargs
        }

    def get_request_credentials(self):
        try:
            authorization = flask.request.headers['Authorization']
        except KeyError:
            return None

        token = self.get_token(authorization)

        try:
            payload = jwt.decode(token, **self.get_jwt_decode_args())
        except InvalidTokenError:
            logger.warning("invalid token", exc_info=True)
            flask.abort(401)

        return self.get_credentials(payload)

    def get_token(self, authorization):
        try:
            scheme, token = authorization.split()
        except ValueError:
            logger.warning("malformed Authorization header", exc_info=True)
            flask.abort(401)

        if scheme != 'Bearer':
            logger.warning("incorrect authentication scheme")
            flask.abort(401)

        return token

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
