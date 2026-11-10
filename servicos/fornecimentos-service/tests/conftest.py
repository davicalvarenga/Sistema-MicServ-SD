"""Dublês das portas da ESP-FRN-001 (§5.1) e utilitários de token para os testes."""

import copy
from contextlib import contextmanager
from decimal import Decimal
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


class FakeRepoFornecimentos:
    """Repositório em memória com transação real (desfaz em exceção) e movimento atômico."""

    def __init__(self):
        self.estado = {"produtos": {}, "fornecimentos": {}, "reservas": {}, "eventos": set()}
        self.trava = threading.RLock()
        self.falhar_insercao = False
        self.falhar_movimento = False
        self.pronto = True

    @contextmanager
    def transacao(self):
        with self.trava:
            copia = copy.deepcopy(self.estado)
            try:
                yield
            except BaseException:
                self.estado = copia
                raise

    def evento_processado(self, event_id):
        return event_id in self.estado["eventos"]

    def registrar_evento_processado(self, event_id):
        self.estado["eventos"].add(event_id)

    def salvar_produto_referencia(self, produto):
        self.estado["produtos"][produto["produto_id"]] = copy.deepcopy(produto)

    def obter_produto_referencia(self, produto_id):
        return copy.deepcopy(self.estado["produtos"].get(produto_id))

    def inserir_fornecimento(self, fornecimento):
        if self.falhar_insercao:
            raise RuntimeError("banco indisponível")
        self.estado["fornecimentos"][fornecimento["fornecimento_id"]] = copy.deepcopy(fornecimento)

    def obter_fornecimento(self, fornecimento_id):
        return copy.deepcopy(self.estado["fornecimentos"].get(fornecimento_id))

    def listar_fornecimentos(self, produto_id, offset, limite):
        itens = [f for f in self.estado["fornecimentos"].values() if produto_id is None or f["produto_id"] == produto_id]
        itens.sort(key=lambda f: (f["criado_em"], f["fornecimento_id"]))
        return copy.deepcopy(itens[offset:offset + limite]), len(itens)

    def aplicar_movimento(self, fornecimento_id, delta_disponivel, delta_reservada, atualizado_em):
        assert isinstance(delta_disponivel, Decimal) and isinstance(delta_reservada, Decimal)
        if self.falhar_movimento:
            raise RuntimeError("falha no banco durante o movimento")
        with self.trava:
            f = self.estado["fornecimentos"].get(fornecimento_id)
            if f is None:
                return None
            disponivel = f["quantidade_disponivel"] + delta_disponivel
            reservada = f["quantidade_reservada"] + delta_reservada
            if disponivel < 0 or reservada < 0:
                return None
            f.update(quantidade_disponivel=disponivel, quantidade_reservada=reservada, atualizado_em=atualizado_em)
            return copy.deepcopy(f)

    def obter_reserva(self, pedido_id, fornecimento_id):
        return copy.deepcopy(self.estado["reservas"].get((pedido_id, fornecimento_id)))

    def salvar_reserva(self, reserva):
        self.estado["reservas"][(reserva["pedido_id"], reserva["fornecimento_id"])] = copy.deepcopy(reserva)

    def disponivel(self):
        return self.pronto


def token(escopo="SUPPLIER", tenant="EMP-34", sub="USR-7", exp=None, chave=PRIVADA, kid=KID, algoritmo="RS256", **extras):
    claims = {"sub": sub, "tenant_id": tenant, "active_scope": escopo,
              "exp": int((exp or T0 + timedelta(hours=1)).timestamp())}
    claims.update(extras)
    for nome in [n for n, v in extras.items() if v is None]:
        claims.pop(nome)
    cabecalho = {"kid": kid} if kid is not None else {}
    return jwt.encode(claims, chave, algorithm=algoritmo, headers=cabecalho)


def auth(escopo="SUPPLIER", **kwargs):
    return {"Authorization": "Bearer " + token(escopo, **kwargs)}


FORNECIMENTO_VALIDO = {"produto_id": "PROD-1", "preco": 5.5, "quantidade_disponivel": 15000, "origem": {"cidade": "Goiânia", "uf": "GO"}}


class Ambiente:
    def __init__(self):
        self.bus = FakeBus()
        self.clock = FakeClock()
        self.repo = FakeRepoFornecimentos()
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


_seq = [0]


def evento(topico, payload, event_id=None, correlation="corr-evt", aggregate=None, timestamp="2026-10-26T13:59:00Z"):
    _seq[0] += 1
    msg = {"eventId": event_id or f"{topico}-{_seq[0]}", "eventType": topico, "eventVersion": "1.0",
           "timestamp": timestamp, "source": "teste", "correlationId": correlation,
           "aggregateId": aggregate, "payload": payload}
    if correlation is None:
        msg.pop("correlationId")
    if aggregate is None:
        msg["aggregateId"] = payload.get("pedidoId") or payload.get("produtoId") if isinstance(payload, dict) else None
    return msg


def produto(produto_id="PROD-1", unidade="L", nome="Leite integral", tipo="REFRIGERADO", **kw):
    return evento("produto_cadastrado", {"produtoId": produto_id, "nome": nome, "unidade": unidade, "tipoTransporte": tipo}, **kw)


def pedido_criado(pedido="PED-1", fornecimento="FORN-1", quantidade=30, **kw):
    return evento("pedido_criado", {"pedidoId": pedido, "negociacaoId": "NEG-7", "compradorId": "EMP-12",
                                     "fornecedorId": "EMP-34", "fornecimentoId": fornecimento, "produtoId": "PROD-1",
                                     "quantidade": quantidade, "valorTotal": 165.0, "status": "CRIADO"}, **kw)


def pedido_atualizado(pedido="PED-1", fornecimento="FORN-1", status="CANCELADO", **kw):
    return evento("pedido_atualizado", {"pedidoId": pedido, "fornecimentoId": fornecimento, "status": status}, **kw)


def entregar(amb, topico, mensagem):
    """Entrega a mensagem ao handler inscrito no tópico, como faria o adaptador de consumo."""
    for handler in amb.bus.handlers[topico]:
        handler(copy.deepcopy(mensagem))


def gravar_fornecimento(amb, disponivel, reservada=0, fid="FORN-1", produto_id="PROD-1", criado_em="2026-10-26T14:00:00Z"):
    amb.repo.estado["fornecimentos"][fid] = {
        "fornecimento_id": fid, "fornecedor_id": "EMP-34", "produto_id": produto_id, "unidade": "L",
        "preco": Decimal("5.5"), "quantidade_disponivel": Decimal(str(disponivel)), "quantidade_reservada": Decimal(str(reservada)),
        "origem": {"cidade": "Goiânia", "uf": "GO"}, "criado_por_usuario_id": "USR-7", "criado_em": criado_em, "atualizado_em": criado_em}
