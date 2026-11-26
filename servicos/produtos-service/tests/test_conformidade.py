"""Testes de conformidade da ESP-PRD-001 v2.0: um teste por critério de aceitação."""

import ast
import logging
import pathlib
import time
from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import (
    KID, OUTRA_PRIVADA, PRIVADA, PRODUTO_VALIDO, T0, Ambiente, FakeBus, FakeChaves, FakeClock,
    FakeRepoProdutos, auth, eh_uuid4, token,
)

URL = "/api/v1/produtos"


def cadastrar(amb, corpo=None, escopo="SUPPLIER", **headers):
    return amb.cliente.post(URL, json=corpo or PRODUTO_VALIDO, headers={**auth(escopo), **headers})


# RF-01 Cadastrar produto

def test_CA01(amb):
    r = cadastrar(amb)
    assert r.status_code == 201
    corpo = r.json()
    assert eh_uuid4(corpo["produto_id"])
    assert corpo == {
        "produto_id": corpo["produto_id"], "nome": "Leite integral", "categoria": "LATICINIOS", "unidade": "L",
        "tipo_transporte": "REFRIGERADO", "peso_unitario_kg": None, "cadastrado_por_empresa_id": "EMP-34",
        "cadastrado_por_usuario_id": "USR-7", "cadastrado_em": "2026-10-26T14:00:00Z",
        "atualizado_em": "2026-10-26T14:00:00Z", "com_movimentacao": False,
    }
    g = amb.cliente.get(f"{URL}/{corpo['produto_id']}", headers=auth("SUPPLIER"))
    assert g.status_code == 200 and g.json() == corpo


def test_CA02(amb):
    r = cadastrar(amb, {"nome": "Soja em grãos", "categoria": "GRAOS", "unidade": "TON", "tipo_transporte": "GRANEL"}, "BUYER")
    assert r.status_code == 201


def test_CA03(amb):
    for escopo in ("CARRIER",):
        r = cadastrar(amb, escopo=escopo)
        assert r.status_code == 403 and r.json()["codigo"] == "PERFIL_NAO_PERMITIDO"
    assert amb.repo.produtos == {} and amb.bus.publicadas == []


@pytest.mark.parametrize("corpo", [
    {**PRODUTO_VALIDO, "nome": "L"},
    {**PRODUTO_VALIDO, "nome": "   "},
    {k: v for k, v in PRODUTO_VALIDO.items() if k != "categoria"},
    {**PRODUTO_VALIDO, "unidade": "litro"},
    {**PRODUTO_VALIDO, "tipo_transporte": "AEREO"},
    {**PRODUTO_VALIDO, "nome": 123},
    {**PRODUTO_VALIDO, "peso_unitario_kg": 0},
    {**PRODUTO_VALIDO, "peso_unitario_kg": -1},
    {**PRODUTO_VALIDO, "peso_unitario_kg": "1.5"},
    {**PRODUTO_VALIDO, "peso_unitario_kg": True},
    {**PRODUTO_VALIDO, "peso_unitario_kg": 1.0005},
    {**PRODUTO_VALIDO, "peso_unitario_kg": 1000000000},
    ["Leite"],
    '{"nome": "Leite",',
])
def test_CA04(amb, corpo):
    if isinstance(corpo, str):
        r = amb.cliente.post(URL, content=corpo, headers={**auth("SUPPLIER"), "Content-Type": "application/json"})
    else:
        r = cadastrar(amb, corpo)
    assert r.status_code == 422 and r.json()["codigo"] == "DADOS_INVALIDOS"
    assert amb.repo.produtos == {} and amb.bus.publicadas == []


def test_CA05(amb):
    corpo = {"nome": "  Leite integral  ", "categoria": " LATICINIOS ", "unidade": "L", "tipo_transporte": "REFRIGERADO",
             "cadastrado_por_empresa_id": "EMP-99"}
    r = cadastrar(amb, corpo)
    assert r.status_code == 201
    assert (r.json()["nome"], r.json()["categoria"], r.json()["cadastrado_por_empresa_id"]) == ("Leite integral", "LATICINIOS", "EMP-34")


def test_CA06(amb):
    amb.repo.falhar_insercao = True
    r = cadastrar(amb)
    assert r.status_code == 500 and r.json()["codigo"] == "ERRO_INTERNO"
    assert amb.bus.publicadas == []


# RF-02 Consultar produto

def test_CA07(amb):
    criado = cadastrar(amb).json()
    r = amb.cliente.get(f"{URL}/{criado['produto_id']}", headers=auth("CARRIER"))
    assert r.status_code == 200 and r.json() == criado


def test_CA08(amb):
    r = amb.cliente.get(f"{URL}/PROD-INEXISTENTE", headers=auth("BUYER"))
    assert r.status_code == 404 and r.json()["codigo"] == "PRODUTO_NAO_ENCONTRADO"


# RF-03 Listar produtos

def _tres_produtos(amb):
    for segundo, (nome, categoria) in enumerate([("Leite", "LATICINIOS"), ("Queijo", "LATICINIOS"), ("Soja", "GRAOS")]):
        amb.clock.agora = T0 + timedelta(seconds=segundo)
        assert cadastrar(amb, {**PRODUTO_VALIDO, "nome": nome, "categoria": categoria}).status_code == 201
    amb.clock.agora = T0


def test_CA09(amb):
    _tres_produtos(amb)
    r = amb.cliente.get(f"{URL}?page=1&size=2", headers=auth("BUYER")).json()
    assert [p["nome"] for p in r["itens"]] == ["Leite", "Queijo"] and (r["page"], r["size"], r["total"]) == (1, 2, 3)
    r = amb.cliente.get(f"{URL}?page=2&size=2", headers=auth("BUYER")).json()
    assert [p["nome"] for p in r["itens"]] == ["Soja"] and r["total"] == 3
    r = amb.cliente.get(f"{URL}?categoria=LATICINIOS", headers=auth("BUYER")).json()
    assert [p["nome"] for p in r["itens"]] == ["Leite", "Queijo"] and (r["page"], r["size"], r["total"]) == (1, 10, 2)


def test_CA10(amb):
    _tres_produtos(amb)
    r = amb.cliente.get(f"{URL}?page=5&size=2", headers=auth("BUYER"))
    assert r.status_code == 200 and r.json()["itens"] == [] and r.json()["total"] == 3


def test_CA11(amb):
    for parametros in ("size=101", "size=0", "page=0", "page=abc", "size=1.5"):
        r = amb.cliente.get(f"{URL}?{parametros}", headers=auth("BUYER"))
        assert r.status_code == 422 and r.json()["codigo"] == "PAGINACAO_INVALIDA", parametros
    assert amb.cliente.get(f"{URL}?size=100", headers=auth("BUYER")).status_code == 200


# RF-04 Publicar evento

def test_CA12(amb):
    r = cadastrar(amb, **{"X-Correlation-Id": "corr-001"})
    pid = r.json()["produto_id"]
    assert len(amb.bus.publicadas) == 1
    pub = amb.bus.publicadas[0]
    assert pub["topic"] == "produto_cadastrado" and pub["key"] == pid
    m = pub["message"]
    assert eh_uuid4(m["eventId"])
    assert {k: m[k] for k in ("eventType", "eventVersion", "timestamp", "source", "correlationId", "aggregateId")} == {
        "eventType": "produto_cadastrado", "eventVersion": "1.0", "timestamp": "2026-10-26T14:00:00.000Z",
        "source": "produtos-service", "correlationId": "corr-001", "aggregateId": pid}
    assert m["payload"] == {"produtoId": pid, "nome": "Leite integral", "categoria": "LATICINIOS", "unidade": "L",
                            "tipoTransporte": "REFRIGERADO", "pesoUnitarioKg": None,
                            "cadastradoPor": {"empresaId": "EMP-34", "usuarioId": "USR-7"},
                            "cadastradoEm": "2026-10-26T14:00:00.000Z"}


def test_CA13(amb):
    for escopo in ("CARRIER",):
        cadastrar(amb, escopo=escopo)
    cadastrar(amb, {**PRODUTO_VALIDO, "unidade": "litro"})
    amb.cliente.post(URL, json=PRODUTO_VALIDO)
    amb.cliente.post(URL, json=PRODUTO_VALIDO, headers={"Authorization": "Bearer " + token(chave=OUTRA_PRIVADA)})
    amb.cliente.post(URL, json=PRODUTO_VALIDO, headers={"Authorization": "Bearer " + token(exp=T0)})
    assert amb.bus.publicadas == []


# RF-05 Autenticação

def test_CA14(amb):
    for cabecalhos in ({}, {"Authorization": "Basic abc"}, {"Authorization": "Bearer "}):
        r = amb.cliente.post(URL, json=PRODUTO_VALIDO, headers=cabecalhos)
        assert r.status_code == 401 and r.json()["codigo"] == "TOKEN_AUSENTE"


def test_CA15(amb):
    r = amb.cliente.post(URL, json=PRODUTO_VALIDO, headers={"Authorization": "Bearer " + token(chave=OUTRA_PRIVADA)})
    assert r.status_code == 401 and r.json()["codigo"] == "TOKEN_INVALIDO"


def test_CA16(amb):
    exp = int((T0 + timedelta(hours=1)).timestamp())
    tokens = [
        token("GERENTE"),
        token("supplier"),
        token(sub=""),
        jwt.encode({"sub": "USR-7", "tenant_id": "EMP-34", "active_scope": "SUPPLIER", "exp": exp}, "segredo-compartilhado",
                   algorithm="HS256", headers={"kid": KID}),
        token(kid="kid-desconhecido"),
    ]
    for t in tokens:
        r = amb.cliente.get(URL, headers={"Authorization": "Bearer " + t})
        assert r.status_code == 401 and r.json()["codigo"] == "TOKEN_INVALIDO"


def test_CA17(amb):
    cabecalho = {"Authorization": "Bearer " + token(exp=T0)}
    r = amb.cliente.get(URL, headers=cabecalho)
    assert r.status_code == 401 and r.json()["codigo"] == "TOKEN_EXPIRADO"
    amb.clock.agora = T0 - timedelta(seconds=1)
    assert amb.cliente.get(URL, headers=cabecalho).status_code == 200


# RF-06 Correlation id

def test_CA18(amb):
    r = amb.cliente.get(f"{URL}/PROD-INEXISTENTE", headers={**auth("BUYER"), "X-Correlation-Id": "corr-404"})
    assert r.status_code == 404 and r.headers["X-Correlation-Id"] == "corr-404" and r.json()["correlationId"] == "corr-404"


def test_CA19(amb):
    for cabecalhos in ({}, {"X-Correlation-Id": "   "}):
        assert eh_uuid4(amb.cliente.get("/health", headers=cabecalhos).headers["X-Correlation-Id"])


# RF-07 Saúde, prontidão e métricas

def test_CA20(amb):
    r = amb.cliente.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "UP", "service": "produtos-service", "timestamp": "2026-10-26T14:00:00Z"}
    r = amb.cliente.get("/health/ready")
    assert r.status_code == 200 and r.json()["status"] == "READY"


def test_CA21(amb):
    amb.bus.pronto = False
    r = amb.cliente.get("/health/ready")
    assert r.status_code == 503 and r.json()["codigo"] == "DEPENDENCIA_INDISPONIVEL"
    assert amb.cliente.get("/health").status_code == 200


def test_CA22(amb):
    cadastrar(amb)
    cadastrar(amb)
    amb.cliente.get(f"{URL}/PROD-INEXISTENTE", headers=auth("BUYER"))
    texto = amb.cliente.get("/metrics").text
    assert 'http_requests_total{service="produtos-service",status="201"} 2' in texto
    assert 'http_requests_total{service="produtos-service",status="404"} 1' in texto


# Requisitos não funcionais

CAMPOS_ERRO = ("type", "title", "status", "detail", "instance", "codigo", "correlationId", "timestamp")


def _verificar_erro(r):
    assert r.headers["content-type"].startswith("application/problem+json")
    corpo = r.json()
    assert all(corpo.get(c) not in (None, "") for c in CAMPOS_ERRO), corpo
    assert corpo["status"] == r.status_code
    assert corpo["type"] == "https://portal-b2b.corp/erros/" + corpo["codigo"].lower().replace("_", "-")


def test_CA23(amb):
    r = amb.cliente.get("/api/v1/inexistente", headers=auth("BUYER"))
    assert r.status_code == 404 and r.json()["codigo"] == "ROTA_NAO_ENCONTRADA"
    _verificar_erro(r)
    r = amb.cliente.patch(f"{URL}/PROD-1", headers=auth("SUPPLIER"))
    assert r.status_code == 405 and r.json()["codigo"] == "METODO_NAO_PERMITIDO"
    _verificar_erro(r)
    respostas = [
        cadastrar(amb, escopo="CARRIER"),
        cadastrar(amb, {**PRODUTO_VALIDO, "unidade": "litro"}),
        amb.cliente.get(f"{URL}?size=101", headers=auth("BUYER")),
        amb.cliente.get(f"{URL}/X", headers=auth("BUYER")),
        amb.cliente.post(URL, json=PRODUTO_VALIDO),
        amb.cliente.get(URL, headers={"Authorization": "Bearer " + token(exp=T0)}),
    ]
    amb.repo.falhar_insercao = True
    respostas.append(cadastrar(amb))
    amb.repo.pronto = False
    respostas.append(amb.cliente.get("/health/ready"))
    for r in respostas:
        _verificar_erro(r)


def test_CA24(amb):
    for i in range(100):
        cadastrar(amb, {**PRODUTO_VALIDO, "nome": f"Produto {i:03d}"})
    cabecalho = auth("BUYER")
    inicio = time.perf_counter()
    for _ in range(500):
        assert amb.cliente.get(f"{URL}?size=100", headers=cabecalho).status_code == 200
    assert time.perf_counter() - inicio < 5


def test_CA25():
    repo = FakeRepoProdutos()
    a = TestClient(create_app(FakeBus(), FakeClock(), repo, FakeChaves()))
    b = TestClient(create_app(FakeBus(), FakeClock(), repo, FakeChaves()))
    pid = a.post(URL, json=PRODUTO_VALIDO, headers=auth()).json()["produto_id"]
    assert b.get(f"{URL}/{pid}", headers=auth()).status_code == 200
    c = TestClient(create_app(FakeBus(), FakeClock(), FakeRepoProdutos(), FakeChaves()))
    assert c.get(f"{URL}/{pid}", headers=auth()).status_code == 404


def test_CA26():
    permitidos = {"fastapi", "pydantic", "starlette", "jwt", "cryptography", "app"}
    import sys
    pasta = pathlib.Path(__file__).resolve().parents[1] / "app"
    for arquivo in pasta.glob("*.py"):
        for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
            modulos = [a.name for a in no.names] if isinstance(no, ast.Import) else (
                [no.module or ""] if isinstance(no, ast.ImportFrom) and no.level == 0 else [])
            for modulo in modulos:
                raiz = modulo.split(".")[0]
                assert raiz in permitidos or raiz in sys.stdlib_module_names, f"{arquivo.name}: {modulo}"


def test_CA27(amb, caplog):
    valor = token()
    with caplog.at_level(logging.DEBUG):
        amb.cliente.post(URL, json=PRODUTO_VALIDO, headers={"Authorization": "Bearer " + valor})
    assert valor not in str(amb.bus.publicadas)
    assert all(valor not in registro.getMessage() for registro in caplog.records)


# RF-01 e RF-04: peso unitário opcional (RN-08)

def test_CA28(amb):
    corpo = {"nome": "Caixa de leite", "categoria": "LATICINIOS", "unidade": "CX", "tipo_transporte": "REFRIGERADO",
             "peso_unitario_kg": 12.35}
    r = cadastrar(amb, corpo)
    assert r.status_code == 201 and r.json()["peso_unitario_kg"] == 12.35
    pid = r.json()["produto_id"]
    assert amb.cliente.get(f"{URL}/{pid}", headers=auth("BUYER")).json() == r.json()
    assert amb.bus.publicadas[0]["message"]["payload"]["pesoUnitarioKg"] == 12.35
    r = cadastrar(amb, {**corpo, "peso_unitario_kg": None})
    assert r.status_code == 201 and r.json()["peso_unitario_kg"] is None
    assert amb.bus.publicadas[1]["message"]["payload"]["pesoUnitarioKg"] is None
    for limite in (0.001, 999999999.999):
        r = cadastrar(amb, {**corpo, "peso_unitario_kg": limite})
        assert r.status_code == 201 and r.json()["peso_unitario_kg"] == limite


# §7.1: emissor, audiência, contexto e serviço de chaves (v1.4)

def test_CA29(amb):
    for t in (token(iss="falsificador"), token(aud="outro-sistema"), token(iss=None), token(aud=None)):
        r = amb.cliente.get(URL, headers={"Authorization": "Bearer " + t})
        assert r.status_code == 401 and r.json()["codigo"] == "TOKEN_INVALIDO"
    r = amb.cliente.get(URL, headers={"Authorization": "Bearer " + token(aud=["b2b-platform", "outro-sistema"])})
    assert r.status_code == 200


def test_CA30(amb):
    sem_contexto = (token(None, tenant=None), token(tenant=""), token(None))
    for t in sem_contexto:
        r = amb.cliente.post(URL, json=PRODUTO_VALIDO, headers={"Authorization": "Bearer " + t})
        assert r.status_code == 403 and r.json()["codigo"] == "CONTEXTO_NAO_SELECIONADO"
        assert r.headers["content-type"].startswith("application/problem+json")
    r = amb.cliente.get(URL, headers={"Authorization": "Bearer " + token(None, tenant=None, exp=T0)})
    assert r.status_code == 401 and r.json()["codigo"] == "TOKEN_EXPIRADO"
    assert amb.repo.produtos == {} and amb.bus.publicadas == []


def test_CA31(amb):
    class ChavesForaDoAr:
        def obter(self, kid):
            raise ConnectionError("JWKS indisponível")

    cliente = TestClient(create_app(amb.bus, amb.clock, amb.repo, ChavesForaDoAr()))
    r = cliente.post(URL, json=PRODUTO_VALIDO, headers=auth())
    assert r.status_code == 503 and r.json()["codigo"] == "DEPENDENCIA_INDISPONIVEL"
    assert amb.repo.produtos == {} and amb.bus.publicadas == []


# v2.0: categoria em lista fixa, alteração e exclusão sem movimentação, consumo de fornecimento_criado

def _fornecimento_criado(amb, produto_id, event_id="evt-forn-1"):
    mensagem = {"eventId": event_id, "eventType": "fornecimento_criado", "eventVersion": "1.0", "timestamp": "2026-10-26T14:01:00Z",
                "source": "fornecimentos-service", "correlationId": "corr-forn", "aggregateId": "FORN-1",
                "payload": {"fornecimentoId": "FORN-1", "produtoId": produto_id}}
    for handler in amb.bus.handlers["fornecimento_criado"]:
        handler(mensagem)


def _publicadas(amb, topico):
    return [p for p in amb.bus.publicadas if p["topic"] == topico]


@pytest.mark.parametrize("categoria", ["Laticínios", "laticinios", "ELETRONICOS", "", 7])
def test_CA32(amb, categoria):
    r = cadastrar(amb, {**PRODUTO_VALIDO, "categoria": categoria})
    assert r.status_code == 422 and r.json()["codigo"] == "DADOS_INVALIDOS"
    assert amb.repo.produtos == {} and amb.bus.publicadas == []


def test_CA33(amb):
    pid = cadastrar(amb).json()["produto_id"]
    amb.clock.agora = T0 + timedelta(minutes=10)
    novo = {"nome": "Leite desnatado", "categoria": "LATICINIOS", "unidade": "CX", "tipo_transporte": "REFRIGERADO",
            "peso_unitario_kg": 12}
    r = amb.cliente.put(f"{URL}/{pid}", json=novo, headers={**auth(), "X-Correlation-Id": "corr-alt"})
    assert r.status_code == 200
    c = r.json()
    assert (c["nome"], c["unidade"], c["peso_unitario_kg"], c["cadastrado_em"], c["atualizado_em"]) == \
        ("Leite desnatado", "CX", 12, "2026-10-26T14:00:00Z", "2026-10-26T14:10:00Z")
    assert amb.cliente.get(f"{URL}/{pid}", headers=auth("BUYER")).json() == c
    [evento] = _publicadas(amb, "produto_atualizado")
    assert evento["key"] == pid and evento["message"]["correlationId"] == "corr-alt"
    assert evento["message"]["payload"] == {
        "produtoId": pid, "nome": "Leite desnatado", "categoria": "LATICINIOS", "unidade": "CX", "tipoTransporte": "REFRIGERADO",
        "pesoUnitarioKg": 12, "atualizadoPor": {"empresaId": "EMP-34", "usuarioId": "USR-7"}, "atualizadoEm": "2026-10-26T14:10:00.000Z"}


def test_CA34(amb):
    pid = cadastrar(amb).json()["produto_id"]
    r = amb.cliente.delete(f"{URL}/{pid}", headers=auth())
    assert r.status_code == 204 and r.content == b""
    assert amb.cliente.get(f"{URL}/{pid}", headers=auth()).status_code == 404
    [evento] = _publicadas(amb, "produto_excluido")
    assert evento["key"] == pid
    assert evento["message"]["payload"] == {"produtoId": pid, "excluidoPor": {"empresaId": "EMP-34", "usuarioId": "USR-7"},
                                            "excluidoEm": "2026-10-26T14:00:00.000Z"}


def test_CA35(amb):
    pid = cadastrar(amb).json()["produto_id"]
    _fornecimento_criado(amb, pid)
    _fornecimento_criado(amb, pid, "evt-forn-2")
    assert amb.cliente.get(f"{URL}/{pid}", headers=auth()).json()["com_movimentacao"] is True
    amb.bus.publicadas.clear()
    r = amb.cliente.put(f"{URL}/{pid}", json=PRODUTO_VALIDO, headers=auth())
    assert r.status_code == 409 and r.json()["codigo"] == "PRODUTO_COM_MOVIMENTACAO"
    r = amb.cliente.delete(f"{URL}/{pid}", headers=auth())
    assert r.status_code == 409 and r.json()["codigo"] == "PRODUTO_COM_MOVIMENTACAO"
    assert amb.repo.produtos[pid]["nome"] == "Leite integral" and amb.bus.publicadas == []


def test_CA36(amb):
    pid = cadastrar(amb).json()["produto_id"]
    for metodo in ("put", "delete"):
        kwargs = {"json": PRODUTO_VALIDO} if metodo == "put" else {}
        r = getattr(amb.cliente, metodo)(f"{URL}/{pid}", headers=auth("CARRIER"), **kwargs)
        assert r.status_code == 403 and r.json()["codigo"] == "PERFIL_NAO_PERMITIDO"
        r = getattr(amb.cliente, metodo)(f"{URL}/PROD-X", headers=auth(), **kwargs)
        assert r.status_code == 404 and r.json()["codigo"] == "PRODUTO_NAO_ENCONTRADO"
    r = amb.cliente.put(f"{URL}/{pid}", json={**PRODUTO_VALIDO, "unidade": "litro"}, headers=auth())
    assert r.status_code == 422 and r.json()["codigo"] == "DADOS_INVALIDOS"
    r = amb.cliente.put(f"{URL}/PROD-X", json={**PRODUTO_VALIDO, "unidade": "litro"}, headers=auth())
    assert r.status_code == 422  # a validação do corpo vem antes da busca do produto
    assert len(amb.bus.publicadas) == 1  # só o produto_cadastrado


def test_CA37(amb):
    for mensagem in ({"eventId": "x", "payload": {}}, {"payload": {"produtoId": "P"}}, "texto"):
        for handler in amb.bus.handlers["fornecimento_criado"]:
            handler(mensagem)
    assert [p["topic"] for p in amb.bus.publicadas] == ["produtos.dlt"] * 3
    assert amb.bus.publicadas[0]["message"]["payload"]["originalEvent"] == {"eventId": "x", "payload": {}}
    amb.bus.publicadas.clear()
    _fornecimento_criado(amb, "PROD-DESCONHECIDO")
    assert amb.bus.publicadas == [] and amb.repo.produtos == {}


def test_CA38(amb):
    pid = cadastrar(amb).json()["produto_id"]
    lido = dict(amb.repo.produtos[pid])
    _fornecimento_criado(amb, pid)
    amb.repo.obter = lambda produto_id: dict(lido)  # leitura antiga: o fornecimento chegou depois da leitura
    amb.bus.publicadas.clear()
    r = amb.cliente.put(f"{URL}/{pid}", json=PRODUTO_VALIDO, headers=auth())
    assert r.status_code == 409 and r.json()["codigo"] == "PRODUTO_COM_MOVIMENTACAO"
    r = amb.cliente.delete(f"{URL}/{pid}", headers=auth())
    assert r.status_code == 409 and pid in amb.repo.produtos and amb.bus.publicadas == []


GRUPO = {"tenant": None, "view_mode": "MACRO_GROUP", "allowed_tenants": ["EMP-34", "EMP-35"], "group_id": "GRP-3"}


def test_CA39(amb):
    """Visão de grupo econômico (MACRO_GROUP): consultas aceitas; cadastro, alteração e exclusão recusados com 403."""
    pid = cadastrar(amb).json()["produto_id"]
    amb.bus.publicadas.clear()
    assert amb.cliente.get(f"{URL}/{pid}", headers=auth("BUYER", **GRUPO)).status_code == 200
    r = amb.cliente.get(URL, headers=auth("BUYER", **GRUPO))
    assert r.status_code == 200 and r.json()["total"] == 1
    for metodo, url, kwargs in (("post", URL, {"json": PRODUTO_VALIDO}), ("put", f"{URL}/{pid}", {"json": PRODUTO_VALIDO}),
                                ("delete", f"{URL}/{pid}", {})):
        r = getattr(amb.cliente, metodo)(url, headers=auth(**GRUPO), **kwargs)
        assert r.status_code == 403 and r.json()["codigo"] == "CONTEXTO_DE_GRUPO_NAO_PERMITIDO"
        assert r.json()["title"] == "Contexto de Grupo Não Permitido"
    assert amb.bus.publicadas == [] and len(amb.repo.produtos) == 1


def test_CA40(amb):
    """Token de grupo sem allowed_tenants válido é inválido; token do login continua pedindo o switch-context."""
    for invalido in ([], None, "EMP-34", [""], [3]):
        r = amb.cliente.get(URL, headers=auth(**{**GRUPO, "allowed_tenants": invalido}))
        assert r.status_code == 401 and r.json()["codigo"] == "TOKEN_INVALIDO"
    r = amb.cliente.get(URL, headers=auth(tenant=None, view_mode="NONE"))
    assert r.status_code == 403 and r.json()["codigo"] == "CONTEXTO_NAO_SELECIONADO"
    r = amb.cliente.get(URL, headers=auth(None, **GRUPO))
    assert r.status_code == 403 and r.json()["codigo"] == "CONTEXTO_NAO_SELECIONADO"


def test_CA41(amb):
    """Catálogo compartilhado: outra empresa e o administrador da empresa alteram e excluem produto sem movimentação."""
    pid = cadastrar(amb).json()["produto_id"]
    r = amb.cliente.put(f"{URL}/{pid}", json={**PRODUTO_VALIDO, "nome": "Leite desnatado"}, headers=auth(tenant="EMP-99"))
    assert r.status_code == 200 and r.json()["nome"] == "Leite desnatado"
    assert amb.bus.publicadas[-1]["message"]["payload"]["atualizadoPor"] == {"empresaId": "EMP-99", "usuarioId": "USR-7"}
    r = amb.cliente.delete(f"{URL}/{pid}", headers=auth("TENANT_ADMIN", tenant="EMP-77"))
    assert r.status_code == 204 and amb.bus.publicadas[-1]["topic"] == "produto_excluido"
    r = cadastrar(amb, escopo="TENANT_ADMIN")
    assert r.status_code == 201 and amb.bus.publicadas[-1]["topic"] == "produto_cadastrado"
