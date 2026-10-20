"""
Suíte de aceitação CONGELADA (Fase 5) — escrita ANTES da geração de código.
Cada teste referencia o ID do critério (RF-xx/CA-yy) e é aplicada IGUALMENTE
aos dois braços (controle e tratamento). Import do app é parametrizado por env.
"""
import os
import importlib
import pytest
from fastapi.testclient import TestClient

APP_MODULE = os.environ.get("APP_MODULE", "treatment.app")  # "control.app" ou "treatment.app"


@pytest.fixture()
def client():
    mod = importlib.import_module(APP_MODULE)
    importlib.reload(mod)
    return TestClient(mod.app)


def _register(client, email="ana@x.com", password="Senha@123"):
    return client.post("/auth/register", json={"email": email, "password": password})


def _token(client, email="ana@x.com", password="Senha@123"):
    _register(client, email, password)
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json().get("access_token") or r.json().get("token")


def _auth(tok):
    return {"Authorization": f"Bearer {tok}"}


# ------- RF-01: cadastro de despesa -------

def test_RF01_CA01_cadastro_valido(client):
    """RF-01/CA-01 (Alta, peso 3): usuário autenticado cadastra despesa válida."""
    tok = _token(client)
    r = client.post("/expenses", headers=_auth(tok), json={
        "description": "Almoço", "amount": 35.50, "date": "2026-01-10", "category": "Alimentacao"})
    assert r.status_code in (200, 201)
    body = r.json()
    assert "id" in body
    assert float(body["amount"]) == 35.50


def test_RF01_CA02_valor_zero_rejeitado(client):
    """RF-01/CA-02 (Alta, peso 3): valor <= 0 é rejeitado, nada é persistido."""
    tok = _token(client)
    r = client.post("/expenses", headers=_auth(tok), json={
        "description": "X", "amount": 0, "date": "2026-01-10", "category": "Outros"})
    assert r.status_code in (400, 422)
    lst = client.get("/expenses", headers=_auth(tok)).json()
    items = lst if isinstance(lst, list) else lst.get("items", [])
    assert len(items) == 0


def test_RF01_CA03_nao_autenticado_bloqueado(client):
    """RF-01/CA-03 (Alta, peso 3, VETO/autorização): sem token retorna 401/403."""
    r = client.post("/expenses", json={
        "description": "X", "amount": 10, "date": "2026-01-10", "category": "Outros"})
    assert r.status_code in (401, 403)


# ------- RF-02: listagem -------

def test_RF02_CA01_lista_somente_do_usuario(client):
    """RF-02/CA-01 (Alta, peso 3): listagem retorna apenas despesas do próprio usuário."""
    tok = _token(client)
    client.post("/expenses", headers=_auth(tok), json={
        "description": "A", "amount": 10, "date": "2026-01-10", "category": "Outros"})
    lst = client.get("/expenses", headers=_auth(tok)).json()
    items = lst if isinstance(lst, list) else lst.get("items", [])
    assert len(items) == 1
    assert items[0]["description"] == "A"


def test_RF02_CA02_isolamento_entre_usuarios(client):
    """RF-02/CA-02 (Alta, peso 3, VETO/IDOR): usuário B não vê despesa de A."""
    tok_a = _token(client, "a@x.com")
    client.post("/expenses", headers=_auth(tok_a), json={
        "description": "SecretoA", "amount": 99, "date": "2026-01-10", "category": "Outros"})
    tok_b = _token(client, "b@x.com")
    lst_b = client.get("/expenses", headers=_auth(tok_b)).json()
    items_b = lst_b if isinstance(lst_b, list) else lst_b.get("items", [])
    assert all(i["description"] != "SecretoA" for i in items_b)
    assert len(items_b) == 0


# ------- RF-03: total -------

def test_RF03_CA01_total_do_periodo(client):
    """RF-03/CA-01 (Média, peso 2): total soma apenas despesas do usuário."""
    tok = _token(client)
    for v in (10.0, 20.5, 4.5):
        client.post("/expenses", headers=_auth(tok), json={
            "description": "d", "amount": v, "date": "2026-01-10", "category": "Outros"})
    r = client.get("/expenses/total", headers=_auth(tok))
    assert r.status_code == 200
    assert abs(float(r.json()["total"]) - 35.0) < 1e-6


# ------- RNF: segurança de senha -------

def test_RNF01_CA01_senha_nao_exposta(client):
    """RNF-01/CA-01 (Alta, peso 3, VETO/privacidade): senha nunca retorna em respostas."""
    r = _register(client, "sec@x.com", "Senha@123")
    assert "Senha@123" not in r.text
    assert "password" not in {k.lower() for k in (r.json() if r.headers.get(
        "content-type", "").startswith("application/json") else {})}


# ------- RNF: validação de email -------

def test_RNF02_CA01_email_invalido_rejeitado(client):
    """RNF-02/CA-01 (Média, peso 2): email em formato inválido é rejeitado no cadastro."""
    r = client.post("/auth/register", json={"email": "sem-arroba", "password": "Senha@123"})
    assert r.status_code in (400, 422)


# Mapa de pesos e veto — usado pelo runner para conformidade ponderada
WEIGHTS = {
    "test_RF01_CA01_cadastro_valido": (3, False),
    "test_RF01_CA02_valor_zero_rejeitado": (3, False),
    "test_RF01_CA03_nao_autenticado_bloqueado": (3, True),
    "test_RF02_CA01_lista_somente_do_usuario": (3, False),
    "test_RF02_CA02_isolamento_entre_usuarios": (3, True),
    "test_RF03_CA01_total_do_periodo": (2, False),
    "test_RNF01_CA01_senha_nao_exposta": (3, True),
    "test_RNF02_CA01_email_invalido_rejeitado": (2, False),
}
