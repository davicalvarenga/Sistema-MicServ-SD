"""Porta ChavesPublicas: chaves RSA do serviço de Autenticação, lidas do JWKS com cache.

O endpoint é o /.well-known/jwks.json do serviço de Autenticação (issue #2), acessado
pelo gateway. As chaves ficam em cache por 1 hora, então não há requisição por token.
"""

import logging

import jwt

logger = logging.getLogger(__name__)


class ChavesJwks:
    def __init__(self, url: str, validade_cache_segundos: int = 3600):
        self._cliente = jwt.PyJWKClient(url, cache_keys=True, max_cached_keys=16, lifespan=validade_cache_segundos)

    def obter(self, kid: str):
        try:
            return self._cliente.get_signing_key(kid).key
        except jwt.PyJWKClientError as erro:
            logger.warning("chave publica nao encontrada para o kid informado: %s", erro)
            return None
