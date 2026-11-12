"""Testes de conformidade da ESP-FRN-001 v1.4: um teste por critério de aceitação."""

import ast
import copy
import logging
import pathlib
import sys
import threading
import time
from datetime import timedelta
from decimal import Decimal

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import (
    FORNECIMENTO_VALIDO, KID, OUTRA_PRIVADA, PRIVADA, T0, Ambiente, FakeBus, FakeChaves, FakeClock,
    FakeRepoFornecimentos, auth, eh_uuid4, entregar, gravar_fornecimento, pedido_atualizado, pedido_criado,
    produto, token,
)

URL = "/api/v1/fornecimentos"


@pytest.fixture
def amb():
    ambiente = Ambiente()
    entregar(ambiente, "produto_cadastrado", produto())
    ambiente.bus.publicadas.clear()
    return ambiente


def cadastrar(amb, corpo=None, escopo="SUPPLIER", **headers):
    return amb.cliente.post(URL, json=FORNECIMENTO_VALIDO if corpo is None else corpo, headers={**auth(escopo), **headers})


def saldo(amb, fid="FORN-1"):
    f = amb.repo.estado["fornecimentos"][fid]
    return f["quantidade_disponivel"], f["quantidade_reservada"]


def publicadas(amb, topico):
    return [p for p in amb.bus.publicadas if p["topic"] == topico]


# RF-01 Cadastrar fornecimento

def test_CA01(amb):
    r = cadastrar(amb)
    assert r.status_code == 201
    corpo = r.json()
    assert eh_uuid4(corpo["fornecimento_id"])
    assert corpo == {
        "fornecimento_id": corpo["fornecimento_id"], "fornecedor_id": "EMP-34", "produto_id": "PROD-1", "unidade": "L",
        "preco": 5.5, "quantidade_disponivel": 15000, "quantidade_reservada": 0, "origem": {"cidade": "Goiânia", "uf": "GO"},
        "criado_por_usuario_id": "USR-7", "criado_em": "2026-10-26T14:00:00Z", "atualizado_em": "2026-10-26T14:00:00Z",
    }
    g = amb.cliente.get(f"{URL}/{corpo['fornecimento_id']}", headers=auth("BUYER"))
    assert g.status_code == 200 and g.json() == corpo


def test_CA02(amb):
    for escopo in ("BUYER", "CARRIER", "TENANT_ADMIN"):
        r = cadastrar(amb, escopo=escopo)
        assert r.status_code == 403 and r.json()["codigo"] == "PERFIL_NAO_PERMITIDO"
    assert amb.repo.estado["fornecimentos"] == {} and amb.bus.publicadas == []


SEM_PRODUTO = {k: v for k, v in FORNECIMENTO_VALIDO.items() if k != "produto_id"}


@pytest.mark.parametrize("corpo", [
    {**FORNECIMENTO_VALIDO, "preco": 0}, {**FORNECIMENTO_VALIDO, "preco": -1}, {**FORNECIMENTO_VALIDO, "preco": "5.50"},
    {**FORNECIMENTO_VALIDO, "preco": 5.555}, {**FORNECIMENTO_VALIDO, "preco": 10000000000}, {**FORNECIMENTO_VALIDO, "preco": True},
    {**FORNECIMENTO_VALIDO, "quantidade_disponivel": 0}, {**FORNECIMENTO_VALIDO, "quantidade_disponivel": 1.234},
    {**FORNECIMENTO_VALIDO, "origem": "Goiânia-GO"}, {**FORNECIMENTO_VALIDO, "origem": {"cidade": "   ", "uf": "GO"}},
    {**FORNECIMENTO_VALIDO, "origem": {"cidade": "a" * 256, "uf": "GO"}}, {**FORNECIMENTO_VALIDO, "origem": {"cidade": "Goiânia"}},
    {**FORNECIMENTO_VALIDO, "origem": {"cidade": "Goiânia", "uf": "go"}}, {**FORNECIMENTO_VALIDO, "origem": {"cidade": "Goiânia", "uf": "XX"}},
    SEM_PRODUTO,
    {**FORNECIMENTO_VALIDO, "produto_id": 1}, ["x"], '{"produto_id": ',
])
def test_CA03(amb, corpo):
    if isinstance(corpo, str):
        r = amb.cliente.post(URL, content=corpo, headers={**auth(), "Content-Type": "application/json"})
    else:
        r = cadastrar(amb, corpo)
    assert r.status_code == 422 and r.json()["codigo"] == "DADOS_INVALIDOS"
    assert amb.repo.estado["fornecimentos"] == {} and amb.bus.publicadas == []


def test_CA04(amb):
    r = cadastrar(amb, {**FORNECIMENTO_VALIDO, "produto_id": "PROD-X"})
    assert r.status_code == 422 and r.json()["codigo"] == "PRODUTO_INEXISTENTE"
    assert amb.bus.publicadas == []


def test_CA05(amb):
    r = cadastrar(amb, {"produto_id": "PROD-1", "preco": 9999999999.99, "quantidade_disponivel": 0.01,
                        "origem": {"cidade": "  Anápolis  ", "uf": " GO "}, "fornecedor_id": "EMP-99"})
    assert r.status_code == 201
    c = r.json()
    assert (c["fornecedor_id"], c["preco"], c["quantidade_disponivel"], c["origem"]) == ("EMP-34", 9999999999.99, 0.01, {"cidade": "Anápolis", "uf": "GO"})


def test_CA06(amb):
    amb.repo.falhar_insercao = True
    r = cadastrar(amb)
    assert r.status_code == 500 and r.json()["codigo"] == "ERRO_INTERNO"
    assert amb.bus.publicadas == []


# RF-02 Consultar fornecimento

def test_CA07(amb):
    gravar_fornecimento(amb, 70, 30)
    r = amb.cliente.get(f"{URL}/FORN-1", headers=auth("TENANT_ADMIN"))
    assert r.status_code == 200 and (r.json()["quantidade_disponivel"], r.json()["quantidade_reservada"]) == (70, 30)


def test_CA08(amb):
    r = amb.cliente.get(f"{URL}/FORN-X", headers=auth("BUYER"))
    assert r.status_code == 404 and r.json()["codigo"] == "FORNECIMENTO_NAO_ENCONTRADO"


def test_CA09(amb):
    gravar_fornecimento(amb, 100)
    for url in (f"{URL}/FORN-1", URL):
        r = amb.cliente.get(url, headers=auth("CARRIER"))
        assert r.status_code == 403 and r.json()["codigo"] == "PERFIL_NAO_PERMITIDO"


# RF-03 Listar fornecimentos

def test_CA10(amb):
    entregar(amb, "produto_cadastrado", produto("PROD-2", unidade="KG"))
    for segundo, (origem, pid) in enumerate([("A", "PROD-1"), ("B", "PROD-2"), ("C", "PROD-1")]):
        amb.clock.agora = T0 + timedelta(seconds=segundo)
        assert cadastrar(amb, {**FORNECIMENTO_VALIDO, "origem": {"cidade": origem, "uf": "GO"}, "produto_id": pid}).status_code == 201
    r = amb.cliente.get(f"{URL}?page=1&size=2", headers=auth("BUYER")).json()
    assert [f["origem"]["cidade"] for f in r["itens"]] == ["A", "B"] and (r["page"], r["size"], r["total"]) == (1, 2, 3)
    r = amb.cliente.get(f"{URL}?produto_id=PROD-1", headers=auth("BUYER")).json()
    assert [f["origem"]["cidade"] for f in r["itens"]] == ["A", "C"] and r["total"] == 2
    r = amb.cliente.get(f"{URL}?page=9&size=2", headers=auth("BUYER"))
    assert r.status_code == 200 and r.json()["itens"] == [] and r.json()["total"] == 3


def test_CA11(amb):
    for parametros in ("size=101", "size=0", "page=0", "page=abc"):
        r = amb.cliente.get(f"{URL}?{parametros}", headers=auth("BUYER"))
        assert r.status_code == 422 and r.json()["codigo"] == "PAGINACAO_INVALIDA", parametros
    assert amb.cliente.get(f"{URL}?size=100", headers=auth("BUYER")).status_code == 200


# RF-04 Publicar fornecimento criado

def test_CA12(amb):
    r = cadastrar(amb, **{"X-Correlation-Id": "corr-001"})
    fid = r.json()["fornecimento_id"]
    assert len(amb.bus.publicadas) == 1
    pub = amb.bus.publicadas[0]
    assert pub["topic"] == "fornecimento_criado" and pub["key"] == fid
    m = pub["message"]
    assert eh_uuid4(m["eventId"])
    assert {k: m[k] for k in ("eventType", "eventVersion", "timestamp", "source", "correlationId", "aggregateId")} == {
        "eventType": "fornecimento_criado", "eventVersion": "1.0", "timestamp": "2026-10-26T14:00:00Z",
        "source": "fornecimentos-service", "correlationId": "corr-001", "aggregateId": fid}
    assert m["payload"] == {"fornecimentoId": fid, "fornecedorId": "EMP-34", "produtoId": "PROD-1", "unidade": "L", "preco": 5.5,
                            "quantidadeDisponivel": 15000, "origem": {"cidade": "Goiânia", "uf": "GO"},
                            "criadoPor": {"empresaId": "EMP-34", "usuarioId": "USR-7"}, "criadoEm": "2026-10-26T14:00:00Z"}


def test_CA13(amb):
    for escopo in ("BUYER", "CARRIER", "TENANT_ADMIN"):
        cadastrar(amb, escopo=escopo)
    cadastrar(amb, {**FORNECIMENTO_VALIDO, "preco": 0})
    cadastrar(amb, {**FORNECIMENTO_VALIDO, "produto_id": "PROD-X"})
    amb.cliente.post(URL, json=FORNECIMENTO_VALIDO)
    amb.cliente.post(URL, json=FORNECIMENTO_VALIDO, headers={"Authorization": "Bearer " + token(chave=OUTRA_PRIVADA)})
    amb.cliente.post(URL, json=FORNECIMENTO_VALIDO, headers={"Authorization": "Bearer " + token(exp=T0)})
    assert amb.bus.publicadas == []


# RF-05 Referência local de produtos

def test_CA14(amb):
    entregar(amb, "produto_cadastrado", produto("PROD-9", unidade="TON", nome="Soja", tipo="GRANEL"))
    assert amb.bus.publicadas == []
    r = cadastrar(amb, {**FORNECIMENTO_VALIDO, "produto_id": "PROD-9"})
    assert r.status_code == 201 and r.json()["unidade"] == "TON"


def test_CA15(amb):
    entregar(amb, "produto_cadastrado", produto("PROD-1", unidade="KG"))
    assert cadastrar(amb).json()["unidade"] == "L"


def test_CA16(amb):
    msg = produto("PROD-8", event_id="E-P1")
    del msg["payload"]["unidade"]
    entregar(amb, "produto_cadastrado", msg)
    dlt = publicadas(amb, "fornecimentos.dlt")
    assert len(dlt) == 1 and dlt[0]["key"] == "PROD-8"
    p = dlt[0]["message"]["payload"]
    assert p["originalEvent"] == msg and p["error"] and p["stackTrace"] == "" and p["failedAtAttempt"] == 1
    r = cadastrar(amb, {**FORNECIMENTO_VALIDO, "produto_id": "PROD-8"})
    assert r.status_code == 422 and r.json()["codigo"] == "PRODUTO_INEXISTENTE"


# RF-06 Reservar estoque

def _ca17(amb):
    gravar_fornecimento(amb, 100)
    amb.clock.agora = T0 + timedelta(minutes=10)
    msg = pedido_criado("PED-1", "FORN-1", 30, correlation="corr-ped")
    entregar(amb, "pedido_criado", msg)
    return msg


def test_CA17(amb):
    _ca17(amb)
    r = amb.cliente.get(f"{URL}/FORN-1", headers=auth("BUYER")).json()
    assert (r["quantidade_disponivel"], r["quantidade_reservada"], r["atualizado_em"]) == (70, 30, "2026-10-26T14:10:00Z")
    assert len(amb.bus.publicadas) == 1
    pub = amb.bus.publicadas[0]
    assert pub["topic"] == "estoque_atualizado" and pub["key"] == "FORN-1" and pub["message"]["correlationId"] == "corr-ped"
    assert pub["message"]["payload"] == {
        "fornecimentoId": "FORN-1", "produtoId": "PROD-1", "fornecedorId": "EMP-34", "operacao": "RESERVA",
        "quantidadeMovimentada": 30, "quantidadeDisponivel": 70, "quantidadeReservada": 30, "pedidoId": "PED-1",
        "atualizadoEm": "2026-10-26T14:10:00Z"}


def test_CA18(amb):
    msg = _ca17(amb)
    amb.bus.publicadas.clear()
    entregar(amb, "pedido_criado", msg)
    assert saldo(amb) == (70, 30) and amb.bus.publicadas == []


def test_CA19(amb):
    _ca17(amb)
    amb.bus.publicadas.clear()
    entregar(amb, "pedido_criado", pedido_criado("PED-1", "FORN-1", 30))
    assert saldo(amb) == (70, 30) and amb.bus.publicadas == []


def test_CA20(amb):
    gravar_fornecimento(amb, 70, 30)
    entregar(amb, "pedido_criado", pedido_criado("PED-2", "FORN-1", 80))
    assert saldo(amb) == (70, 30)
    assert len(amb.bus.publicadas) == 1
    pub = amb.bus.publicadas[0]
    assert pub["topic"] == "reserva_estoque_recusada" and pub["key"] == "PED-2"
    assert pub["message"]["payload"] == {"pedidoId": "PED-2", "fornecimentoId": "FORN-1", "quantidadeSolicitada": 80,
                                         "quantidadeDisponivel": 70, "motivo": "ESTOQUE_INSUFICIENTE",
                                         "recusadoEm": "2026-10-26T14:00:00Z"}


def test_CA21(amb):
    gravar_fornecimento(amb, 70, 30)
    entregar(amb, "pedido_criado", pedido_criado("PED-3", "FORN-1", 70))
    assert saldo(amb) == (0, 100)
    pubs = publicadas(amb, "estoque_atualizado")
    assert len(pubs) == 1 and pubs[0]["message"]["payload"]["operacao"] == "RESERVA" and pubs[0]["message"]["payload"]["quantidadeDisponivel"] == 0


def test_CA22(amb):
    entregar(amb, "pedido_criado", pedido_criado("PED-4", "FORN-X", 10))
    assert len(amb.bus.publicadas) == 1
    pub = amb.bus.publicadas[0]
    assert pub["topic"] == "reserva_estoque_recusada" and pub["key"] == "PED-4"
    assert pub["message"]["payload"]["motivo"] == "FORNECIMENTO_INEXISTENTE" and pub["message"]["payload"]["quantidadeDisponivel"] is None


def test_CA23(amb):
    gravar_fornecimento(amb, 100)
    msg = pedido_criado("PED-5", "FORN-1", 30, event_id="E-K1")
    del msg["payload"]["fornecimentoId"]
    entregar(amb, "pedido_criado", msg)
    assert saldo(amb) == (100, 0)
    assert len(amb.bus.publicadas) == 1
    pub = amb.bus.publicadas[0]
    assert pub["topic"] == "fornecimentos.dlt" and pub["key"] == "PED-5" and pub["message"]["payload"]["originalEvent"] == msg


def _defeitos():
    base = pedido_criado("PED-9", "FORN-1", 10)
    casos = []
    for quantidade in (0, -5, "30", 1.234, True):
        m = copy.deepcopy(base); m["payload"]["quantidade"] = quantidade; casos.append(m)
    m = copy.deepcopy(base); m["payload"]["pedidoId"] = "  "; casos.append(m)
    m = copy.deepcopy(base); del m["payload"]; casos.append(m)
    m = copy.deepcopy(base); m["payload"] = ["nao", "objeto"]; casos.append(m)
    m = copy.deepcopy(base); del m["eventId"]; casos.append(m)
    return casos


@pytest.mark.parametrize("msg", _defeitos())
def test_CA24(amb, msg):
    gravar_fornecimento(amb, 100)
    entregar(amb, "pedido_criado", msg)
    assert saldo(amb) == (100, 0)
    assert [p["topic"] for p in amb.bus.publicadas] == ["fornecimentos.dlt"]
    sem_chave = pedido_criado("PED-0", "FORN-1", 0)
    del sem_chave["eventId"]; del sem_chave["aggregateId"]
    amb.bus.publicadas.clear()
    entregar(amb, "pedido_criado", sem_chave)
    assert amb.bus.publicadas[0]["key"] == "desconhecido"


def test_CA25(amb):
    msg = pedido_criado("PED-D", "FORN-1", 0, event_id="E-DUP")
    entregar(amb, "pedido_criado", msg)
    entregar(amb, "pedido_criado", msg)
    assert len(publicadas(amb, "fornecimentos.dlt")) == 2


def test_CA26(amb):
    gravar_fornecimento(amb, 100)
    amb.repo.falhar_movimento = True
    msg = pedido_criado("PED-6", "FORN-1", 10)
    entregar(amb, "pedido_criado", msg)
    assert amb.repo.estado["reservas"] == {} and msg["eventId"] not in amb.repo.estado["eventos"]
    assert publicadas(amb, "estoque_atualizado") == []
    dlt = publicadas(amb, "fornecimentos.dlt")
    assert len(dlt) == 1 and dlt[0]["message"]["payload"]["stackTrace"] != ""


# RF-07 Liberar ou dar baixa

def test_CA27(amb):
    _ca17(amb)
    amb.bus.publicadas.clear()
    entregar(amb, "pedido_atualizado", pedido_atualizado("PED-1", "FORN-1", "CANCELADO"))
    assert saldo(amb) == (100, 0)
    pubs = publicadas(amb, "estoque_atualizado")
    assert len(pubs) == 1 and pubs[0]["key"] == "FORN-1"
    p = pubs[0]["message"]["payload"]
    assert (p["operacao"], p["quantidadeMovimentada"], p["quantidadeDisponivel"], p["quantidadeReservada"], p["pedidoId"]) == ("LIBERACAO", 30, 100, 0, "PED-1")
    amb.bus.publicadas.clear()
    entregar(amb, "pedido_atualizado", pedido_atualizado("PED-1", "FORN-1", "VENDA_CONCLUIDA"))
    assert saldo(amb) == (100, 0) and amb.bus.publicadas == []


def test_CA28(amb):
    _ca17(amb)
    amb.bus.publicadas.clear()
    entregar(amb, "pedido_atualizado", pedido_atualizado("PED-1", "FORN-1", "VENDA_CONCLUIDA"))
    assert saldo(amb) == (70, 0)
    p = publicadas(amb, "estoque_atualizado")[0]["message"]["payload"]
    assert (p["operacao"], p["quantidadeMovimentada"], p["quantidadeDisponivel"], p["quantidadeReservada"]) == ("BAIXA", 30, 70, 0)


def test_CA29(amb):
    gravar_fornecimento(amb, 100)
    entregar(amb, "pedido_atualizado", pedido_atualizado("PED-7", "FORN-1", "CANCELADO"))
    entregar(amb, "pedido_criado", pedido_criado("PED-7", "FORN-1", 40))
    assert saldo(amb) == (100, 0) and amb.bus.publicadas == []


def test_CA30(amb):
    _ca17(amb)
    amb.bus.publicadas.clear()
    entregar(amb, "pedido_atualizado", pedido_atualizado("PED-1", "FORN-1", "FRETE_SELECIONADO"))
    assert saldo(amb) == (70, 30) and amb.bus.publicadas == []
    msg = pedido_atualizado("PED-1", "FORN-1", "CANCELADO")
    del msg["payload"]["status"]
    entregar(amb, "pedido_atualizado", msg)
    assert [(p["topic"], p["key"]) for p in amb.bus.publicadas] == [("fornecimentos.dlt", "PED-1")]


# RF-08 Autenticação

def test_CA31(amb):
    for cabecalhos in ({}, {"Authorization": "Basic abc"}, {"Authorization": "Bearer "}):
        r = amb.cliente.post(URL, json=FORNECIMENTO_VALIDO, headers=cabecalhos)
        assert r.status_code == 401 and r.json()["codigo"] == "TOKEN_AUSENTE"


def test_CA32(amb):
    r = amb.cliente.post(URL, json=FORNECIMENTO_VALIDO, headers={"Authorization": "Bearer " + token(chave=OUTRA_PRIVADA)})
    assert r.status_code == 401 and r.json()["codigo"] == "TOKEN_INVALIDO"


def test_CA33(amb):
    exp = int((T0 + timedelta(hours=1)).timestamp())
    tokens = [
        token("GERENTE"), token("supplier"), token("BUYER", sub=""),
        jwt.encode({"sub": "USR-7", "tenant_id": "EMP-34", "active_scope": "BUYER", "exp": exp}, "segredo-compartilhado",
                   algorithm="HS256", headers={"kid": KID}),
        token("BUYER", kid="kid-desconhecido"),
    ]
    for t in tokens:
        r = amb.cliente.get(URL, headers={"Authorization": "Bearer " + t})
        assert r.status_code == 401 and r.json()["codigo"] == "TOKEN_INVALIDO"


def test_CA34(amb):
    cabecalho = {"Authorization": "Bearer " + token("BUYER", exp=T0)}
    r = amb.cliente.get(URL, headers=cabecalho)
    assert r.status_code == 401 and r.json()["codigo"] == "TOKEN_EXPIRADO"
    amb.clock.agora = T0 - timedelta(seconds=1)
    assert amb.cliente.get(URL, headers=cabecalho).status_code == 200


# RF-09 Correlation id

def test_CA35(amb):
    r = amb.cliente.get(f"{URL}/FORN-X", headers={**auth("BUYER"), "X-Correlation-Id": "corr-404"})
    assert r.status_code == 404 and r.headers["X-Correlation-Id"] == "corr-404" and r.json()["correlationId"] == "corr-404"
    assert eh_uuid4(amb.cliente.get("/health").headers["X-Correlation-Id"])


def test_CA36(amb):
    gravar_fornecimento(amb, 100)
    entregar(amb, "pedido_criado", pedido_criado("PED-8", "FORN-1", 10, correlation=None))
    assert eh_uuid4(publicadas(amb, "estoque_atualizado")[0]["message"]["correlationId"])


# RF-10 Saúde, prontidão e métricas

def test_CA37(amb):
    r = amb.cliente.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "UP", "service": "fornecimentos-service", "timestamp": "2026-10-26T14:00:00Z"}
    assert amb.cliente.get("/health/ready").json()["status"] == "READY"


def test_CA38(amb):
    amb.repo.pronto = False
    r = amb.cliente.get("/health/ready")
    assert r.status_code == 503 and r.json()["codigo"] == "DEPENDENCIA_INDISPONIVEL"


def test_CA39(amb):
    cadastrar(amb)
    amb.cliente.get(f"{URL}/FORN-X", headers=auth("BUYER"))
    amb.cliente.get(f"{URL}/FORN-X", headers=auth("BUYER"))
    texto = amb.cliente.get("/metrics").text
    assert 'http_requests_total{service="fornecimentos-service",status="201"} 1' in texto
    assert 'http_requests_total{service="fornecimentos-service",status="404"} 2' in texto


# Requisitos não funcionais

CAMPOS_ERRO = ("type", "title", "status", "detail", "instance", "codigo", "correlationId", "timestamp")


def _verificar_erro(r):
    assert r.headers["content-type"].startswith("application/problem+json")
    corpo = r.json()
    assert all(corpo.get(c) not in (None, "") for c in CAMPOS_ERRO), corpo
    assert corpo["status"] == r.status_code
    assert corpo["type"] == "https://portal-b2b.corp/erros/" + corpo["codigo"].lower().replace("_", "-")


def test_CA40(amb):
    r = amb.cliente.get("/api/v1/inexistente", headers=auth("BUYER"))
    assert r.status_code == 404 and r.json()["codigo"] == "ROTA_NAO_ENCONTRADA"
    _verificar_erro(r)
    r = amb.cliente.delete(f"{URL}/FORN-1", headers=auth("SUPPLIER"))
    assert r.status_code == 405 and r.json()["codigo"] == "METODO_NAO_PERMITIDO"
    _verificar_erro(r)
    respostas = [
        cadastrar(amb, escopo="BUYER"), cadastrar(amb, {**FORNECIMENTO_VALIDO, "preco": 0}),
        cadastrar(amb, {**FORNECIMENTO_VALIDO, "produto_id": "PROD-X"}), amb.cliente.get(f"{URL}?size=101", headers=auth("BUYER")),
        amb.cliente.get(f"{URL}/FORN-X", headers=auth("BUYER")), amb.cliente.post(URL, json=FORNECIMENTO_VALIDO),
        amb.cliente.get(URL, headers={"Authorization": "Bearer " + token("BUYER", exp=T0)}),
    ]
    amb.repo.falhar_insercao = True
    respostas.append(cadastrar(amb))
    amb.repo.pronto = False
    respostas.append(amb.cliente.get("/health/ready"))
    for r in respostas:
        _verificar_erro(r)


def test_CA41(amb):
    r = cadastrar(amb, {**FORNECIMENTO_VALIDO, "quantidade_disponivel": 0.3, "preco": 0.07})
    assert r.status_code == 201 and r.json()["preco"] == 0.07
    fid = r.json()["fornecimento_id"]
    amb.bus.publicadas.clear()
    for i in range(3):
        entregar(amb, "pedido_criado", pedido_criado(f"PED-F{i}", fid, 0.1))
    pubs = publicadas(amb, "estoque_atualizado")
    assert len(pubs) == 3 and all(p["message"]["payload"]["operacao"] == "RESERVA" for p in pubs)
    assert saldo(amb, fid) == (Decimal("0"), Decimal("0.3"))


def test_CA42(amb):
    gravar_fornecimento(amb, 10)
    barreira = threading.Barrier(20)

    def entregar_em_thread(i):
        barreira.wait()
        entregar(amb, "pedido_criado", pedido_criado(f"PED-C{i:02d}", "FORN-1", 1))

    threads = [threading.Thread(target=entregar_em_thread, args=(i,)) for i in range(1, 21)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(publicadas(amb, "estoque_atualizado")) == 10
    assert len(publicadas(amb, "reserva_estoque_recusada")) == 10
    assert saldo(amb) == (0, 10)


def test_CA43(amb):
    gravar_fornecimento(amb, 1000)
    inicio = time.perf_counter()
    for i in range(300):
        entregar(amb, "pedido_criado", pedido_criado(f"PED-P{i:03d}", "FORN-1", 1))
    assert time.perf_counter() - inicio < 3 and saldo(amb) == (700, 300)
    for i in range(100):
        gravar_fornecimento(amb, 5, fid=f"FORN-L{i:03d}")
    cabecalho = auth("BUYER")
    inicio = time.perf_counter()
    for _ in range(500):
        assert amb.cliente.get(f"{URL}?size=100", headers=cabecalho).status_code == 200
    assert time.perf_counter() - inicio < 5


def test_CA44():
    repo = FakeRepoFornecimentos()
    a, b = Ambiente(), Ambiente()
    for amb in (a, b):
        amb.repo = repo
    clientes = [TestClient(create_app(FakeBus(), FakeClock(), repo, FakeChaves())) for _ in range(2)]
    repo.salvar_produto_referencia({"produto_id": "PROD-1", "nome": "Leite", "unidade": "L", "tipo_transporte": "REFRIGERADO",
                                    "ativo": True, "versao_evento": "2026-10-26T13:00:00Z"})
    fid = clientes[0].post(URL, json=FORNECIMENTO_VALIDO, headers=auth()).json()["fornecimento_id"]
    assert clientes[1].get(f"{URL}/{fid}", headers=auth("BUYER")).status_code == 200
    outro = TestClient(create_app(FakeBus(), FakeClock(), FakeRepoFornecimentos(), FakeChaves()))
    assert outro.get(f"{URL}/{fid}", headers=auth("BUYER")).status_code == 404


def test_CA45():
    permitidos = {"fastapi", "pydantic", "starlette", "jwt", "cryptography", "app"}
    pasta = pathlib.Path(__file__).resolve().parents[1] / "app"
    for arquivo in pasta.glob("*.py"):
        for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
            modulos = [a.name for a in no.names] if isinstance(no, ast.Import) else (
                [no.module or ""] if isinstance(no, ast.ImportFrom) and no.level == 0 else [])
            for modulo in modulos:
                raiz = modulo.split(".")[0]
                assert raiz in permitidos or raiz in sys.stdlib_module_names, f"{arquivo.name}: {modulo}"


def test_CA46(amb):
    cadastrar(amb)
    _ca17(amb)
    amb.clock.agora = T0
    gravar_fornecimento(amb, 70, 30)
    entregar(amb, "pedido_criado", pedido_criado("PED-2", "FORN-1", 80))
    m = pedido_criado("PED-5", "FORN-1", 30)
    del m["payload"]["fornecimentoId"]
    entregar(amb, "pedido_criado", m)
    ids = set()
    for pub in amb.bus.publicadas:
        msg = pub["message"]
        assert msg["aggregateId"] == pub["key"] and msg["eventType"] == pub["topic"] and msg["eventVersion"] == "1.0"
        assert msg["source"] == "fornecimentos-service" and eh_uuid4(msg["eventId"]) and msg["eventId"] not in ids
        ids.add(msg["eventId"])
    chaves = {pub["topic"]: pub["key"] for pub in amb.bus.publicadas}
    assert chaves["estoque_atualizado"] == "FORN-1" and chaves["reserva_estoque_recusada"] == "PED-2" and chaves["fornecimentos.dlt"] == "PED-5"


def test_CA47(amb, caplog):
    valor = token()
    with caplog.at_level(logging.DEBUG):
        amb.cliente.post(URL, json=FORNECIMENTO_VALIDO, headers={"Authorization": "Bearer " + valor})
    assert valor not in str(amb.bus.publicadas)
    assert all(valor not in registro.getMessage() for registro in caplog.records)


# §7.1: emissor, audiência, contexto e serviço de chaves (v1.4)

def test_CA48(amb):
    for t in (token("BUYER", iss="falsificador"), token("BUYER", aud="outro-sistema"), token("BUYER", iss=None), token("BUYER", aud=None)):
        r = amb.cliente.get(URL, headers={"Authorization": "Bearer " + t})
        assert r.status_code == 401 and r.json()["codigo"] == "TOKEN_INVALIDO"
    r = amb.cliente.get(URL, headers={"Authorization": "Bearer " + token("BUYER", aud=["b2b-platform", "outro-sistema"])})
    assert r.status_code == 200


def test_CA49(amb):
    sem_contexto = (token(None, tenant=None), token("BUYER", tenant=""), token(None))
    for t in sem_contexto:
        r = amb.cliente.post(URL, json=FORNECIMENTO_VALIDO, headers={"Authorization": "Bearer " + t})
        assert r.status_code == 403 and r.json()["codigo"] == "CONTEXTO_NAO_SELECIONADO"
        assert r.headers["content-type"].startswith("application/problem+json")
    r = amb.cliente.get(URL, headers={"Authorization": "Bearer " + token(None, tenant=None, exp=T0)})
    assert r.status_code == 401 and r.json()["codigo"] == "TOKEN_EXPIRADO"
    assert amb.repo.estado["fornecimentos"] == {} and amb.bus.publicadas == []


def test_CA50(amb):
    class ChavesForaDoAr:
        def obter(self, kid):
            raise ConnectionError("JWKS indisponível")

    cliente = TestClient(create_app(amb.bus, amb.clock, amb.repo, ChavesForaDoAr()))
    r = cliente.post(URL, json=FORNECIMENTO_VALIDO, headers=auth())
    assert r.status_code == 503 and r.json()["codigo"] == "DEPENDENCIA_INDISPONIVEL"
    assert amb.repo.estado["fornecimentos"] == {} and amb.bus.publicadas == []
