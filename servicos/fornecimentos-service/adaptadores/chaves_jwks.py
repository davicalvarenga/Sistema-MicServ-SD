"""Porta ChavesPublicas: chaves RSA do serviço de Autenticação, lidas do JWKS com cache.

O endpoint é o /.well-known/jwks.json do serviço de Autenticação (issue #2), acessado
pelo gateway. As chaves ficam em cache por 1 hora, então não há requisição por token.

- `kid` desconhecido: busca o JWKS de novo (a Autenticação pode ter trocado a chave), mas
  no máximo uma vez a cada `intervalo_minimo_segundos`. Tokens com `kid` inventado não
  conseguem fazer o serviço chamar a Autenticação a cada requisição. Se a chave continuar
  desconhecida, devolve None (o serviço responde 401).
- JWKS fora do ar ou ilegível: lança a exceção (o serviço responde 503, e não 401).

Este arquivo é idêntico em produtos-service e fornecimentos-service.
"""

import logging
import threading
import time

import jwt

logger = logging.getLogger(__name__)


class ChavesJwks:
    def __init__(self, url: str, validade_cache_segundos: int = 3600, intervalo_minimo_segundos: float = 5.0,
                 relogio=time.monotonic):
        self._cliente = jwt.PyJWKClient(url, cache_keys=True, max_cached_keys=16, lifespan=validade_cache_segundos)
        self._intervalo = intervalo_minimo_segundos
        self._relogio = relogio
        self._ultima_atualizacao: float | None = None
        self._trava = threading.Lock()

    def obter(self, kid: str):
        try:
            chave = self._procurar(self._cliente.get_signing_keys(), kid)
            if chave is not None:
                return chave
            with self._trava:
                agora = self._relogio()
                if self._ultima_atualizacao is not None and agora - self._ultima_atualizacao < self._intervalo:
                    return None
                self._ultima_atualizacao = agora
            return self._procurar(self._cliente.get_signing_keys(refresh=True), kid)
        except jwt.PyJWKClientConnectionError:
            logger.warning("servico de chaves (JWKS) indisponivel")
            raise
        except jwt.PyJWKClientError as erro:
            # JWKS sem chaves de assinatura ou com formato inesperado: nenhuma chave serve para o token
            logger.warning("JWKS sem chave utilizavel: %s", erro)
            return None

    @staticmethod
    def _procurar(chaves, kid: str):
        for chave in chaves:
            if chave.key_id == kid:
                return chave.key
        return None
