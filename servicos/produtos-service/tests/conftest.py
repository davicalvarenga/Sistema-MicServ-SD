"""Dublês das portas da ESP-PRD-001 (§5.1) e utilitários de token para os testes."""

import copy
import threading
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.main import create_app

T0 = datetime(2026, 10, 26, 14, 0, 0, tzinfo=timezone.utc)


def _par_rsa():
    privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = privada.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    return pem, privada.public_key()


PRIVADA, PUBLICA = _par_rsa()
OUTRA_PRIVADA, _ = _par_rsa()
KID = "chave-teste-1"


class FakeClock:
    def __init__(self, agora=T0):
        self.agora = agora

    def now(self):
        return self.agora


class FakeBus:
    def __init__(self):
        self.publicadas = []
        self.handlers = {}
        self.pronto = True

    def publish(self, topic, key, message):
        self.publicadas.append({"topic": topic, "key": key, "message": copy.deepcopy(message)})
        for handler in self.handlers.get(topic, []):
            handler(copy.deepcopy(message))

    def subscribe(self, topic, handler):
        self.handlers.setdefault(topic, []).append(handler)

    def disponivel(self):
        return self.pronto


class FakeChaves:
    def __init__(self):
        self.chaves = {KID: PUBLICA}

    def obter(self, kid):
        return self.chaves.get(kid)


class FakeRepoProdutos:
    def __init__(self):
        self.produtos = {}
        self.falhar_insercao = False
        self.pronto = True
        self.trava = threading.RLock()

    def inserir(self, produto):
        if self.falhar_insercao:
            raise RuntimeError("banco indisponível")
        with self.trava:
            self.produtos[produto["produto_id"]] = copy.deepcopy(produto)

    def obter(self, produto_id):
        produto = self.produtos.get(produto_id)
        return copy.deepcopy(produto) if produto else None

    def listar(self, categoria, offset, limite):
        itens = [p for p in self.produtos.values() if categoria is None or p["categoria"] == categoria]
        itens.sort(key=lambda p: (p["cadastrado_em"], p["produto_id"]))
        return copy.deepcopy(itens[offset:offset + limite]), len(itens)

    def disponivel(self):
        return self.pronto


def token(escopo="SUPPLIER", tenant="EMP-34", sub="USR-7", exp=None, chave=PRIVADA, kid=KID, algoritmo="RS256", **extras):
    claims = {"sub": sub, "tenant_id": tenant, "active_scope": escopo, "iss": "identity-service", "aud": "b2b-platform",
              "exp": int((exp or T0 + timedelta(hours=1)).timestamp())}
    claims.update(extras)
    for nome in [n for n, v in extras.items() if v is None]:
        claims.pop(nome)
    cabecalho = {"kid": kid} if kid is not None else {}
    return jwt.encode(claims, chave, algorithm=algoritmo, headers=cabecalho)


def auth(escopo="SUPPLIER", **kwargs):
    return {"Authorization": "Bearer " + token(escopo, **kwargs)}


PRODUTO_VALIDO = {"nome": "Leite integral", "categoria": "LATICINIOS", "unidade": "L", "tipo_transporte": "REFRIGERADO"}


class Ambiente:
    def __init__(self):
        self.bus = FakeBus()
        self.clock = FakeClock()
        self.repo = FakeRepoProdutos()
        self.chaves = FakeChaves()
        self.cliente = TestClient(create_app(self.bus, self.clock, self.repo, self.chaves))


@pytest.fixture
def amb():
    return Ambiente()


def eh_uuid4(valor):
    try:
        return uuid.UUID(valor).version == 4
    except (ValueError, TypeError, AttributeError):
        return False
