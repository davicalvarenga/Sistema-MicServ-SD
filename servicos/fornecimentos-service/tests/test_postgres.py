"""Testes de integração do adaptador PostgreSQL (rodam só com PG_ADMIN_DSN e KIT_INIT_SQL definidos).

Montam um banco novo com o script do kit de infraestrutura e a proposta de DDL do grupo,
conectam como svc_fornecimentos e exercitam o adaptador e o serviço completo.
"""

import os
import pathlib
import threading
import uuid
from datetime import datetime, timezone
from decimal import Decimal

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
    yield ADMIN.replace("dbname=postgres", f"dbname={nome}").replace("user=postgres", "user=svc_fornecimentos")
    admin.cursor().execute(f"DROP DATABASE {nome} WITH (FORCE)")
    admin.close()


@pytest.fixture
def repo(dsn_servico):
    from adaptadores.postgres import RepositorioFornecimentosPostgres
    return RepositorioFornecimentosPostgres(dsn_servico)


def _produto(repo, pid):
    with repo.transacao():
        repo.salvar_produto_referencia({"produto_id": pid, "nome": "Leite", "unidade": "L", "tipo_transporte": "REFRIGERADO",
                                        "ativo": True, "versao_evento": "2026-10-26T13:00:00Z"})


def _fornecimento(repo, fid, pid, disponivel):
    _produto(repo, pid)
    with repo.transacao():
        repo.inserir_fornecimento({
            "fornecimento_id": fid, "fornecedor_id": "EMP-34", "produto_id": pid, "unidade": "L", "preco": Decimal("5.50"),
            "quantidade_disponivel": Decimal(disponivel), "quantidade_reservada": Decimal("0"), "origem": {"cidade": "Goiânia", "uf": "GO"},
            "criado_por_usuario_id": "USR-7", "criado_em": "2026-10-26T14:00:00Z", "atualizado_em": "2026-10-26T14:00:00Z"})


def test_conexao_e_permissoes(repo):
    assert repo.disponivel()


def test_movimento_condicional(repo):
    fid = "F-" + uuid.uuid4().hex[:6]
    _fornecimento(repo, fid, "P-" + fid, "100")
    agora = datetime(2026, 10, 26, 14, 10, tzinfo=timezone.utc)
    with repo.transacao():
        f = repo.aplicar_movimento(fid, Decimal("-30"), Decimal("30"), agora)
    assert (f["quantidade_disponivel"], f["quantidade_reservada"], f["atualizado_em"]) == (Decimal("70.00"), Decimal("30.00"), "2026-10-26T14:10:00Z")
    with repo.transacao():
        assert repo.aplicar_movimento(fid, Decimal("-80"), Decimal("80"), agora) is None
        assert repo.aplicar_movimento("inexistente", Decimal("-1"), Decimal("1"), agora) is None
    assert repo.obter_fornecimento(fid)["quantidade_disponivel"] == Decimal("70.00")


def test_transacao_desfeita_em_excecao(repo):
    fid = "F-" + uuid.uuid4().hex[:6]
    _fornecimento(repo, fid, "P-" + fid, "10")
    with pytest.raises(RuntimeError):
        with repo.transacao():
            repo.aplicar_movimento(fid, Decimal("-5"), Decimal("5"), datetime.now(timezone.utc))
            repo.registrar_evento_processado("ev-" + fid)
            raise RuntimeError("falha simulada")
    assert repo.obter_fornecimento(fid)["quantidade_disponivel"] == Decimal("10.00")
    assert not repo.evento_processado("ev-" + fid)


def test_reservas_concorrentes_nao_deixam_saldo_negativo(repo):
    fid = "F-" + uuid.uuid4().hex[:6]
    _fornecimento(repo, fid, "P-" + fid, "10")
    resultados = []
    barreira = threading.Barrier(5)

    def reservar():
        barreira.wait()
        for _ in range(4):
            with repo.transacao():
                resultados.append(repo.aplicar_movimento(fid, Decimal("-1"), Decimal("1"), datetime.now(timezone.utc)) is not None)

    threads = [threading.Thread(target=reservar) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    f = repo.obter_fornecimento(fid)
    assert resultados.count(True) == 10 and resultados.count(False) == 10
    assert (f["quantidade_disponivel"], f["quantidade_reservada"]) == (Decimal("0.00"), Decimal("10.00"))


def test_reserva_e_cancelamento_sem_fornecimento(repo):
    with repo.transacao():
        repo.salvar_reserva({"pedido_id": "PED-X", "fornecimento_id": "FORN-INEXISTENTE", "quantidade": Decimal("0"),
                             "situacao": "CANCELADA_SEM_RESERVA", "criado_em": "2026-10-26T14:00:00Z", "atualizado_em": "2026-10-26T14:00:00Z"})
    assert repo.obter_reserva("PED-X", "FORN-INEXISTENTE")["situacao"] == "CANCELADA_SEM_RESERVA"


def test_fluxo_completo_com_o_servico(repo):
    """create_app com o repositório real: cadastro pela API, reserva e cancelamento por evento."""
    from app.main import create_app
    from tests.conftest import FakeBus, FakeChaves, FakeClock, auth, entregar, pedido_atualizado, pedido_criado, produto

    bus = FakeBus()
    cliente = TestClient(create_app(bus, FakeClock(), repo, FakeChaves()))
    pid = "PROD-" + uuid.uuid4().hex[:6]

    class Amb:
        pass

    amb = Amb()
    amb.bus = bus
    entregar(amb, "produto_cadastrado", produto(pid))
    r = cliente.post("/api/v1/fornecimentos", json={"produto_id": pid, "preco": 0.07, "quantidade_disponivel": 0.3,
                                                    "origem": {"cidade": "Brasília", "uf": "DF"}},
                     headers=auth())
    assert r.status_code == 201, r.text
    fid = r.json()["fornecimento_id"]
    for i in range(3):
        entregar(amb, "pedido_criado", pedido_criado(f"PED-{fid}-{i}", fid, 0.1))
    entregar(amb, "pedido_criado", pedido_criado(f"PED-{fid}-extra", fid, 0.1))
    entregar(amb, "pedido_atualizado", pedido_atualizado(f"PED-{fid}-0", fid, "CANCELADO"))
    g = cliente.get(f"/api/v1/fornecimentos/{fid}", headers=auth("BUYER")).json()
    assert (g["preco"], g["quantidade_disponivel"], g["quantidade_reservada"]) == (0.07, 0.1, 0.2)
    assert g["origem"] == {"cidade": "Brasília", "uf": "DF"}
    topicos = [p["topic"] for p in bus.publicadas]
    assert topicos.count("estoque_atualizado") == 4 and topicos.count("reserva_estoque_recusada") == 1
    lista = cliente.get(f"/api/v1/fornecimentos?produto_id={pid}", headers=auth("BUYER")).json()
    assert lista["total"] == 1 and lista["itens"][0]["fornecimento_id"] == fid
