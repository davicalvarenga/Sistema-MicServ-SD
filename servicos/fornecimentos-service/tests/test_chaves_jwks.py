"""Testes do adaptador ChavesJwks contra um servidor JWKS local (arquivo idêntico nos dois serviços)."""

import http.server
import json
import threading

import jwt
import pytest
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from jwt.algorithms import RSAAlgorithm

from adaptadores.chaves_jwks import ChavesJwks
from tests.conftest import OUTRA_PRIVADA, PUBLICA

OUTRA_PUBLICA = load_pem_private_key(OUTRA_PRIVADA, password=None).public_key()


class ServidorJwks:
    """Servidor HTTP local que serve o JWKS e conta as requisições."""

    def __init__(self):
        self.chaves = {"chave-1": PUBLICA}
        self.requisicoes = 0
        servidor = self

        class Tratador(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                servidor.requisicoes += 1
                corpo = []
                for kid, publica in servidor.chaves.items():
                    jwk = json.loads(RSAAlgorithm.to_jwk(publica))
                    jwk.update({"kid": kid, "use": "sig", "alg": "RS256"})
                    corpo.append(jwk)
                dados = json.dumps({"keys": corpo}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(dados)

            def log_message(self, *args):
                pass

        self._http = http.server.HTTPServer(("127.0.0.1", 0), Tratador)
        self.url = f"http://127.0.0.1:{self._http.server_address[1]}/.well-known/jwks.json"
        self._thread = threading.Thread(target=self._http.serve_forever, daemon=True)
        self._thread.start()

    def parar(self):
        self._http.shutdown()
        self._http.server_close()


class RelogioFalso:
    def __init__(self):
        self.agora = 1000.0

    def __call__(self):
        return self.agora


@pytest.fixture
def servidor():
    s = ServidorJwks()
    yield s
    s.parar()


def test_chave_conhecida_e_cache(servidor):
    chaves = ChavesJwks(servidor.url)
    chave = chaves.obter("chave-1")
    assert chave is not None and chave.public_numbers() == PUBLICA.public_numbers()
    chaves.obter("chave-1")
    assert servidor.requisicoes == 1  # a segunda leitura vem do cache


def test_kid_desconhecido_nao_busca_o_jwks_a_cada_requisicao(servidor):
    relogio = RelogioFalso()
    chaves = ChavesJwks(servidor.url, relogio=relogio)
    assert chaves.obter("chave-1") is not None
    inicial = servidor.requisicoes
    for _ in range(10):
        assert chaves.obter("inventado") is None
    assert servidor.requisicoes == inicial + 1  # só uma nova busca no intervalo de 5 s
    relogio.agora += 5
    assert chaves.obter("inventado") is None
    assert servidor.requisicoes == inicial + 2  # passado o intervalo, busca de novo


def test_chave_nova_da_autenticacao_e_encontrada(servidor):
    relogio = RelogioFalso()
    chaves = ChavesJwks(servidor.url, relogio=relogio)
    assert chaves.obter("chave-1") is not None
    servidor.chaves["chave-2"] = OUTRA_PUBLICA
    assert chaves.obter("chave-2") is not None


def test_jwks_fora_do_ar_lanca_excecao():
    servidor = ServidorJwks()
    url = servidor.url
    servidor.parar()
    with pytest.raises(jwt.PyJWKClientConnectionError):
        ChavesJwks(url).obter("chave-1")
