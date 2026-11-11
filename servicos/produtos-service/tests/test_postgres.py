"""Testes de integração do adaptador PostgreSQL (rodam só com PG_ADMIN_DSN e KIT_INIT_SQL definidos)."""

import os
import pathlib
import uuid

import psycopg2
import pytest
from fastapi.testclient import TestClient

ADMIN = os.environ.get("PG_ADMIN_DSN")
KIT_SQL = os.environ.get("KIT_INIT_SQL")
DDL = pathlib.Path(__file__).resolve().parents[3] / "docs" / "banco" / "01-proposta-ddl-produtos-fornecimentos.sql"

pytestmark = pytest.mark.skipif(not (ADMIN and KIT_SQL), reason="PG_ADMIN_DSN e KIT_INIT_SQL não definidos")


@pytest.fixture(scope="module")
def dsn_servico():
    nome = "portal_b2b_teste_" + uuid.uuid4().hex[:8]
    admin = psycopg2.connect(ADMIN)
    admin.autocommit = True
    admin.cursor().execute(f"CREATE DATABASE {nome}")
    banco = psycopg2.connect(ADMIN.replace("dbname=postgres", f"dbname={nome}"))
    banco.autocommit = True
    with banco.cursor() as cursor:
        cursor.execute(pathlib.Path(KIT_SQL).read_text(encoding="utf-8").replace("portal_b2b", nome))
        cursor.execute(DDL.read_text(encoding="utf-8"))
    banco.close()
    yield ADMIN.replace("dbname=postgres", f"dbname={nome}").replace("user=postgres", "user=svc_produtos")
    admin.cursor().execute(f"DROP DATABASE {nome} WITH (FORCE)")
    admin.close()


def test_fluxo_completo_com_o_servico(dsn_servico):
    from adaptadores.postgres import RepositorioProdutosPostgres
    from app.main import create_app
    from tests.conftest import PRODUTO_VALIDO, FakeBus, FakeChaves, FakeClock, auth

    repo = RepositorioProdutosPostgres(dsn_servico)
    assert repo.disponivel()
    cliente = TestClient(create_app(FakeBus(), FakeClock(), repo, FakeChaves()))
    criado = cliente.post("/api/v1/produtos", json=PRODUTO_VALIDO, headers=auth()).json()
    assert cliente.get(f"/api/v1/produtos/{criado['produto_id']}", headers=auth("BUYER")).json() == criado
    cliente.post("/api/v1/produtos", json={**PRODUTO_VALIDO, "nome": "Soja", "categoria": "GRAOS"}, headers=auth("BUYER"))
    lista = cliente.get("/api/v1/produtos?categoria=LATICINIOS", headers=auth("BUYER")).json()
    assert lista["total"] == 1 and lista["itens"][0] == criado
    assert cliente.get("/api/v1/produtos?size=1&page=2", headers=auth("BUYER")).json()["total"] == 2
    caixa = cliente.post("/api/v1/produtos", json={**PRODUTO_VALIDO, "unidade": "CX", "peso_unitario_kg": 999999999.999},
                         headers=auth()).json()
    assert caixa["peso_unitario_kg"] == 999999999.999
    assert cliente.get(f"/api/v1/produtos/{caixa['produto_id']}", headers=auth("BUYER")).json() == caixa


def test_outbox_publica_produto_cadastrado(dsn_servico):
    """Com o BarramentoOutbox, o evento fica na tabela produtos.outbox até o publicador enviá-lo ao Kafka."""
    from adaptadores.outbox import BarramentoOutbox
    from adaptadores.postgres import RepositorioProdutosPostgres
    from app.main import create_app
    from tests.conftest import PRODUTO_VALIDO, FakeChaves, FakeClock, auth

    class KafkaFalso:
        def __init__(self):
            self.publicadas, self.fora = [], False

        def publish(self, topic, key, message):
            if self.fora:
                raise RuntimeError("broker fora")
            self.publicadas.append((topic, key, message))

        def subscribe(self, topic, handler):
            raise AssertionError("o produtos-service não consome tópicos")

        def disponivel(self):
            return not self.fora

    repo = RepositorioProdutosPostgres(dsn_servico)
    kafka = KafkaFalso()
    kafka.fora = True
    bus = BarramentoOutbox(repo.pool, "produtos", kafka)
    cliente = TestClient(create_app(bus, FakeClock(), repo, FakeChaves()))
    criado = cliente.post("/api/v1/produtos", json={**PRODUTO_VALIDO, "unidade": "CX", "peso_unitario_kg": 1.5},
                          headers={**auth(), "X-Correlation-Id": "corr-outbox"})
    assert criado.status_code == 201  # o Kafka fora não impede o cadastro
    assert bus.publicar_pendentes() == 0 and kafka.publicadas == []
    kafka.fora = False
    assert bus.publicar_pendentes() == 1
    topico, chave, mensagem = kafka.publicadas[0]
    pid = criado.json()["produto_id"]
    assert (topico, chave, mensagem["aggregateId"], mensagem["correlationId"]) == ("produto_cadastrado", pid, pid, "corr-outbox")
    assert mensagem["payload"]["pesoUnitarioKg"] == 1.5 and mensagem["payload"]["nome"] == "Leite integral"
    assert bus.publicar_pendentes() == 0
